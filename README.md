Third Eye for the Blind (Capstone Project)
📌 Overview

Third Eye for the Blind is a wearable AI-powered assistive device designed to help visually impaired users navigate the world safely.
Using a camera + onboard processing + audio feedback, the system identifies objects, obstacles, and contextual cues in real time.

The project applies advanced Computer Vision, Multimodal AI, and Agentic AI pipelines to deliver real-time scene understanding through simple, intuitive audio instructions.

🎯 Core Objective

To build a lightweight, reliable wearable that:

Detects objects & obstacles

Recognizes people and key landmarks

Provides real-time audio feedback

Helps users navigate safely without human assistance

🔍 System Architecture

Camera Module → captures real-time video

OpenCV Pipeline → preprocessing, object tracking, optical flow

FastAPI Backend → sends preprocessed frames to LLM/Vision model

Gemini Vision API → object detection, environment description

Google TTS → converts output into audio

Wearable Speaker / Earbuds → plays navigation instructions

🧠 AI Components
Computer Vision (Local)

Edge detection

Motion tracking

Obstacle proximity estimation

Low-light enhancement

Multimodal LLM (Cloud)

Gemini Vision returns:

Object names

Relative positions (“chair on your left”, “person ahead 3 meters”)

Scene description

Danger alerts

Agentic Logic

Prioritizes hazardous objects

Generates simple navigation instructions

Avoids overloading the user with too many details

🔌 Tech Stack

Python, OpenCV

FastAPI

Gemini Vision API

Google Text-to-Speech

Raspberry Pi / Jetson Nano (optional)

Wireless earbuds / vibration motor

📱 User Experience Flow

User wears the device

Camera captures scene

Edge CV model filters + preprocesses

Gemini Vision interprets the environment

Audio output guides user

Repeats continuously with <300ms latency

🧪 Testing & Validation

Indoor navigation tests

Outdoor obstacle detection

Low-light scenarios

Moving object tracking

Latency + stability checks

🔮 Future Enhancements

Offline object detection with YOLO-Nano

Path planning (SLAM-based)

Voice interaction

Haptic feedback

GPS integration for outdoor navigation
