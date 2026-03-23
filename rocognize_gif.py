import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.vision import drawing_utils
from mediapipe.tasks.python.vision import drawing_styles

def draw_landmarks_on_image(rgb_image, detection_result):
    pose_landmarks_list = detection_result.pose_landmarks
    
    # 4채널(RGBA)일 경우 3채널(RGB)로 변환 (에러 방지)
    if rgb_image.shape[2] == 4:
        rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGBA2RGB)
    
    # annotated_image = np.copy(rgb_image)
    annotated_image = rgb_image
    
    pose_landmark_style = drawing_styles.get_default_pose_landmarks_style()
    pose_connection_style = drawing_utils.DrawingSpec(color=(0, 255, 0), thickness=2)

    for pose_landmarks in pose_landmarks_list:
        drawing_utils.draw_landmarks(
            image=annotated_image,
            landmark_list=pose_landmarks,
            connections=vision.PoseLandmarksConnections.POSE_LANDMARKS,
            landmark_drawing_spec=pose_landmark_style,
            connection_drawing_spec=pose_connection_style)

    return annotated_image

# --- 메인 실행부 ---

# STEP 1: PoseLandmarker 설정 (VIDEO 모드 사용 필수)
base_options = python.BaseOptions(model_asset_path='pose_landmarker_lite.task')
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO, # GIF 재생을 위해 VIDEO 모드로 설정
    output_segmentation_masks=True)

with vision.PoseLandmarker.create_from_options(options) as detector:
    
    # STEP 2: GIF 파일을 비디오 객체로 열기
    cap = cv2.VideoCapture("test.gif")
    
    # GIF의 FPS(재생 속도) 가져오기
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0: fps = 10 # FPS 정보가 없으면 기본값 설정

    print("GIF 애니메이션 분석 중... 종료하려면 창에서 'q'를 누르세요.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            # GIF가 끝나면 다시 처음으로 가거나(반복) 종료합니다.
            break 

        # STEP 3: 프레임 전처리 (BGR -> RGB)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # 비디오 모드에서는 각 프레임의 타임스탬프(ms)가 필요합니다.
        frame_timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))

        # STEP 4: 현재 프레임 포즈 감지
        detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)

        # STEP 5: 결과 시각화
        annotated_image = draw_landmarks_on_image(rgb_frame, detection_result)
        
        # 다시 BGR로 변환하여 창에 표시
        bgr_image = cv2.cvtColor(annotated_image, cv2.COLOR_RGB2BGR)
        cv2.imshow('MediaPipe Pose Detection (GIF)', bgr_image)

        # GIF 재생 속도에 맞춰 대기
        if cv2.waitKey(int(500/fps)) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()