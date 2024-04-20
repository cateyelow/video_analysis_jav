import cv2
import numpy as np
import os
from deepface import DeepFace
from nudenet import NudeDetector
import tempfile
from tqdm import tqdm
from YOLOv8_face import YOLOv8_face

yolo = YOLOv8_face(path="weights/yolov8n-face.onnx", conf_thres=0.8, iou_thres=0.5)


def yolo_face_detection(frame):
    try:
        boxes, scores, classids, kpts = yolo.detect(frame)
        return boxes, scores, classids, kpts
    except:
        return [], [], [], []


def crop_face_frames(frames, padding_ratio=0.3):
    try:
        final_frames = []
        face_detected = False
        crop_width, crop_height = None, None

        for frame in frames:
            boxes, scores, classids, kpts = yolo_face_detection(frame)
            if len(boxes) > 0:
                box = boxes[0]
                face_center_x = int(box[0] + box[2] // 2)
                face_center_y = int(box[1] + box[3] // 2)

                if not face_detected:
                    aspect_ratio = 9 / 16
                    crop_width = int(box[2] / aspect_ratio)
                    crop_height = int(box[3])
                    face_detected = True

                # 패딩 추가
                padding_x = int(crop_width * padding_ratio)
                padding_y = int(crop_height * padding_ratio)
                crop_x1 = max(0, face_center_x - crop_width // 2 - padding_x)
                crop_y1 = max(0, face_center_y - crop_height // 2 - padding_y)
                crop_x2 = min(
                    frame.shape[1], face_center_x + crop_width // 2 + padding_x
                )
                crop_y2 = min(
                    frame.shape[0], face_center_y + crop_height // 2 + padding_y
                )

                cropped_frame = frame[crop_y1:crop_y2, crop_x1:crop_x2]
                final_frames.append(cropped_frame)
            else:
                if face_detected:
                    final_frames.append(frames[-1])
                else:
                    continue

        return final_frames, crop_width + padding_x * 2, crop_height + padding_y * 2

    except:
        return [], 0, 0


def extract_faces(
    video_path: str,
    output_folder: str,
    processed_videos_file: str,
    face_count_threshold: float = 0.9,
):
    os.makedirs(output_folder, exist_ok=True)

    # 이미 처리된 동영상인지 확인
    processed_videos = set()
    if os.path.exists(processed_videos_file):
        with open(processed_videos_file, "r") as file:
            processed_videos = set(line.strip() for line in file)

    video_name = os.path.relpath(video_path, "videos")  # videos 폴더로부터의 상대 경로
    if video_name in processed_videos:
        print(f"Video {video_name} already processed. Skipping.")
        return

    # 동영상 파일 열기
    cap = cv2.VideoCapture(video_path)

    # 동영상 정보 가져오기
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # NSFW 감지기 초기화
    nude_detector = NudeDetector()

    # 변수 초기화
    clip_frames = []
    clip_count = 0
    processing_duration = min(
        20 * 60 * fps, total_frames
    )  # 10분 또는 전체 프레임 수 중 작은 값
    valid_frames = 0

    # tqdm 진행 표시줄 초기화
    progress_bar = tqdm(total=processing_duration, unit="frames", desc=video_name)

    SKIP = fps
    SAVE_SECONDS = 6
    skip_frames = SKIP
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 진행 상황 업데이트
        progress_bar.update(1)

        clip_frames.append(frame)
        if skip_frames > 0:
            skip_frames -= 1
            continue
        else:
            skip_frames = SKIP

        current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

        # 초반 10분만 처리
        if current_frame > processing_duration:
            break

        # 얼굴 감지
        try:
            boxes, scores, classids, kpts = yolo_face_detection(frame)
            face_count = len(boxes)
        except:
            face_count = 0

        # NSFW 감지
        with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
            cv2.imwrite(temp_file.name, frame)
            nude_detections = nude_detector.detect(temp_file.name)
            nsfw_labels = [detection["class"] for detection in nude_detections]
            nsfw_detected = any(
                label in nsfw_labels
                for label in [
                    "FEMALE_GENITALIA_COVERED",
                    "BUTTOCKS_EXPOSED",
                    "FEMALE_BREAST_EXPOSED",
                    "FEMALE_GENITALIA_EXPOSED",
                    "MALE_BREAST_EXPOSED",
                    "ANUS_EXPOSED",
                    "MALE_GENITALIA_EXPOSED",
                ]
            )

        # 미소 감지
        if face_count == 1:
            try:
                facial_analysis = DeepFace.analyze(frame, actions=["emotion"])
                dominant_emotion = facial_analysis[0]["dominant_emotion"]
                smiling_detected = dominant_emotion == "happy"
            except:
                smiling_detected = False
        else:
            smiling_detected = False

        # print(
        #     f"Frame {current_frame}: {face_count} faces, NSFW: {nsfw_detected}, len(clip_frames): {len(clip_frames)}, valid_frames: {valid_frames}, {(valid_frames * SKIP) >= face_count_threshold * SAVE_SECONDS * fps}"
        # )
        # 클립 프레임 수집
        if face_count == 1 and not nsfw_detected and not smiling_detected:
            valid_frames += 1

        if nsfw_detected and current_frame > 10 * 60 * fps:
            break

        # 10초 분량의 클립이 모였으면 저장
        if len(clip_frames) >= SAVE_SECONDS * fps:
            if (valid_frames * SKIP) >= face_count_threshold * SAVE_SECONDS * fps:
                clip_path = os.path.join(
                    output_folder, f"{video_name.split('/')[0]}_clip_{clip_count}.mp4"
                )
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                resized_clip_frames, crop_width, crop_height = crop_face_frames(
                    clip_frames
                )
                if len(resized_clip_frames) == 0:
                    clip_frames = []
                    valid_frames = 0
                    continue

                out = cv2.VideoWriter(clip_path, fourcc, fps, (crop_width, crop_height))
                for clip_frame in resized_clip_frames:
                    out.write(clip_frame)
                out.release()
                clip_count += 1
            clip_frames = []
            valid_frames = 0

    # 마지막 클립 저장
    if len(clip_frames) >= SAVE_SECONDS * fps:
        if (valid_frames * SKIP) >= face_count_threshold * SAVE_SECONDS * fps:
            clip_path = os.path.join(
                output_folder, f"{video_name.split('/')[0]}_clip_{clip_count}.mp4"
            )
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(clip_path, fourcc, fps, (width, height))
            for clip_frame in clip_frames:
                out.write(clip_frame)
            out.release()

    cap.release()
    cv2.destroyAllWindows()

    # 처리된 동영상 파일명 저장
    with open(processed_videos_file, "a") as file:
        file.write(video_name + "\n")

    # 진행 표시줄 종료
    progress_bar.close()


def process_videos(
    video_folder: str,
    output_folder: str,
    processed_videos_file: str,
    face_count_threshold: float = 0.9,
):
    os.makedirs(output_folder, exist_ok=True)

    for root, dirs, files in os.walk(video_folder):
        for file in files:
            video_path = os.path.join(root, file)
            if os.path.isfile(video_path) and video_path.lower().endswith(
                (".mp4", ".avi", ".mov")
            ):
                extract_faces(
                    video_path,
                    output_folder,
                    processed_videos_file,
                    face_count_threshold,
                )


if __name__ == "__main__":
    video_folder = "videos"
    output_folder = "output"
    processed_videos_file = "processed_videos.txt"
    face_count_threshold = 0.9
    process_videos(
        video_folder, output_folder, processed_videos_file, face_count_threshold
    )
