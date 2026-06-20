# VELORA
### Violation Evaluation and Lane Orchestration for Real-time Road Automation

**An AI-powered Smart Traffic Management System** that detects street violations, analyzes real-time traffic, identifies road damage (potholes and cracks), and dynamically controls traffic signals — all on existing CCTV infrastructure, with zero new hardware required.

![License](https://img.shields.io/badge/license-Apache%202.0-blue)
![Python](https://img.shields.io/badge/python-97.1%25-yellow)
![Status](https://img.shields.io/badge/status-graduation%20project-orange)

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Objectives](#objectives)
- [System Architecture](#system-architecture)
- [Core Modules](#core-modules)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Datasets](#datasets)
- [Impact & Innovation](#impact--innovation)
- [Demo](#demo)
- [Roadmap](#roadmap)
- [Team](#team)
- [References](#references)
- [License](#license)

---

## Overview

VELORA is a unified AI platform for intelligent road monitoring, urban violation detection, road surface assessment, and adaptive traffic management — built entirely on top of **existing camera infrastructure**.

The system runs four cooperating modules:

1. **Street Violation Detection**
2. **Pothole Detection & Road Damage Assessment**
3. **Traffic Signal Controller**
4. **n8n Incident Management Pipeline**

At its core, VELORA processes every frame through a **3-model perception pipeline** — **YOLOv8 → DeepLabV3+ → MiDaS** — combining object detection, pixel-level sidewalk segmentation, and monocular depth estimation to make context-aware, depth-informed violation decisions instead of relying on a single naive detector.

All detections feed into an event-driven **n8n** workflow that automatically dispatches alerts to enforcement bureaus, municipal maintenance teams, and the emergency preemption protocol — with a **Streamlit dashboard** giving authorities real-time visibility and final human review before any citation becomes formal enforcement.

## Problem Statement

Urban streets in Egyptian cities face a set of compounding issues that current solutions don't address together:

- **Sidewalk violations** (illegal vendors, blocked pedestrian paths) force pedestrians into vehicle lanes.
- **Road surface deterioration** (potholes) goes undetected for long periods due to manual, scheduled inspections — increasing vehicle damage and maintenance costs.
- **Fixed-time traffic signals** ignore real-time traffic density, causing unnecessary delays during peak hours.
- **Emergency vehicles** face intersection delays with no consistent prioritization mechanism, threatening response times.
- **Existing solutions are fragmented and reactive**, typically relying on expensive dedicated hardware, with no integration between violation detection, road assessment, and signal control.

## Objectives

| # | Objective |
|---|-----------|
| 1 | Design an integrated AI pipeline combining **YOLOv8**, **DeepLabV3+**, and **MiDaS** with a rule-based `ViolationEngine` for depth-aware sidewalk violation detection. |
| 2 | Develop severity-classified pothole detection (low / medium / high) using YOLOv8 fine-tuned on Egyptian road imagery, with automated municipal dispatch. |
| 3 | Build a formally specified, FSM-based adaptive traffic signal controller (`LaneOrchestrator`) with pedestrian safety constraints and emergency vehicle preemption. |
| 4 | Deliver a Streamlit authority dashboard and n8n automation pipeline with full audit logging, validated through integration testing across images, videos, and live streams. |

## System Architecture

```
                         ┌──────────────────────┐
   CCTV / Video Feed ──▶ │   Perception Pipeline │
                         │  YOLOv8 → DeepLabV3+   │
                         │        → MiDaS         │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
     ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐
     │ ViolationEngine │  │ Pothole Detector  │  │ Traffic Density  │
     │ (sidewalk rules)│  │ + Severity Class. │  │     Model        │
     └────────┬────────┘  └────────┬─────────┘  └────────┬─────────┘
              │                    │                      │
              └─────────────┬──────┴──────────┬───────────┘
                             ▼                 ▼
                    ┌─────────────────┐  ┌─────────────────┐
                    │  n8n Incident   │  │  LaneOrchestrator│
                    │  Mgmt Pipeline  │  │   (FSM signal    │
                    │  (alerts/audit) │  │    controller)   │
                    └────────┬────────┘  └────────┬────────┘
                             │                     │
                             ▼                     ▼
                    ┌─────────────────────────────────────┐
                    │     Streamlit Authority Dashboard     │
                    │  live monitoring · historical reports │
                    └───────────────────────────────────────┘
```

## Core Modules

### 1. Violation Engine
Depth-aware sidewalk violation detection combining:
- **YOLOv8** for object detection
- **DeepLabV3+** for pixel-level sidewalk segmentation
- **MiDaS** monocular depth estimation, used to correct for camera perspective distortion

Single-model systems tend to produce high false-positive rates because of perspective distortion alone. By incorporating depth context, the `ViolationEngine` filters these out, achieving a meaningfully lower false-positive rate.

### 2. Pothole Detection & Road Damage Assessment
- YOLOv8 fine-tuned on Egyptian road imagery
- Severity classification: **low / medium / high**
- Automated municipal dispatch via the n8n pipeline

### 3. LaneOrchestrator (Adaptive Traffic Signal Controller)
- Formally specified **Finite State Machine (FSM)** design
- Congestion-based phase duration algorithm
- Pedestrian constraint enforcement
- Emergency vehicle preemption protocol
- Built on an `asyncio` pipeline with a simulation/test harness and audit logging

### 4. n8n Incident Management Pipeline
- Event-driven automation connecting detections to real-world action
- Dispatches alerts to enforcement bureaus, municipal maintenance, and the emergency preemption protocol
- Full audit logging for traceability
- Target: detection → alert → authority notification in **under 2 minutes**

### 5. Streamlit Authority Dashboard
- Real-time monitoring of violations, road damage, signals, and alerts
- Historical reporting
- Human-in-the-loop review before any citation becomes formal enforcement

## Key Features

- ✅ Real-time violation detection via a 3-model pipeline (YOLOv8 + DeepLabV3+ + MiDaS)
- ✅ Pothole detection and severity classification with automated maintenance alerts
- ✅ Adaptive traffic signal control with emergency vehicle preemption (FSM-based)
- ✅ Interactive Streamlit dashboard with live monitoring and historical reporting
- ✅ Runs entirely on **existing CCTV infrastructure** — no new hardware required
- ✅ End-to-end incident management: detection → alert → authority notification in under 2 minutes

## Tech Stack

| Category | Technologies |
|---|---|
| Object Detection | [YOLOv8](https://docs.ultralytics.com) (Ultralytics) |
| Semantic Segmentation | DeepLabV3+ |
| Depth Estimation | MiDaS (Intel ISL) |
| Signal Control | Custom FSM (`LaneOrchestrator`), `asyncio` |
| Automation / Workflow | [n8n](https://docs.n8n.io) |
| Dashboard | [Streamlit](https://streamlit.io) |
| ML Frameworks | [PyTorch](https://pytorch.org/docs), [OpenCV](https://docs.opencv.org) |
| Testing | `pytest`, custom simulation harness |
| Deployment Targets (planned) | Azure / AWS |

## Datasets

- **BDD100K** — urban scene detection
- **RDD2022** — road damage detection
- Custom **Egyptian road footage** — collected and annotated by the team (Cairo street footage + road damage)

## Impact & Innovation

- Automates pedestrian safety enforcement and removes sidewalk obstructions at a scale manual monitoring cannot match in dense Egyptian urban environments.
- Shifts road maintenance from **reactive to proactive**: severity-classified pothole data maps directly to municipal repair prioritization, reducing long-term infrastructure costs.
- **Core innovation — depth-aware 3-model pipeline:** single-model systems suffer from high false-positive rates due to camera perspective distortion. VELORA's `ViolationEngine` uses MiDaS depth estimation to correct for this, significantly reducing false positives compared to single-model approaches.
- Directly supports **Egypt Vision 2030** — smart city development, digital urban infrastructure, and public safety through AI-driven automation.
- Modular architecture supports city-wide deployment, cloud scaling (Azure/AWS), and integration with smart city platforms, all without replacing existing CCTV infrastructure.

## Demo

A demo video and live dashboard walkthrough are available here:
📁 [Demo / Dashboard (Google Drive)](https://drive.google.com/drive/folders/1W1W9GIbKBIgqMCQhBviRm8cMClHgXY-C)

> **Note:** The current version processes pre-recorded footage and images. Live CCTV stream integration is part of the roadmap below.

## Roadmap

**Performance & Optimization**
- Integrate an RL agent to replace the rule-based phase duration calculation
- Train on historical congestion sequences from operational deployment using the existing simulation harness

**Feature Enhancement**
- Multilingual dashboard (Arabic + English) for Egyptian municipal contexts
- Mobile app for field inspection teams to review and acknowledge alerts

**Testing & Validation**
- Broader field testing on live Egyptian road environments beyond recorded footage
- Live CCTV stream integration (current version processes pre-recorded footage and images)

**Integration & Deployment**
- Hardware abstraction layer for physical traffic signal controllers (RS-485, NEMA TS-2, NTCIP)
- Physical emergency preemption hardware integration (Opticom infrared, GPS-based systems)

**Scale & Wider Reach**
- Cloud deployment (Azure/AWS) for multi-city scalable operation
- Multi-intersection green wave coordination along arterial corridors

**Research & Impact**
- Publish findings on depth-aware violation detection and FSM-based adaptive signal control
- Open-source the platform to support research and smart city adoption

## Team

| Member | Contributions |
|---|---|
| **Basma Hassan Qutb** | `ViolationEngine` implementation, YOLOv8 multi-class detection, MiDaS depth pipeline, DeepLabV3+ segmentation, zone calibration |
| **Wesam Fathy Masoud Omar** | Cairo street footage dataset collection & annotation, Egyptian road damage dataset, YOLOv8 fine-tuning, traffic density model, model evaluation |
| **Tasneem Faisal Makhlouf** | `LaneOrchestrator` FSM design, `asyncio` pipeline, congestion-based phase duration algorithm, pedestrian constraint enforcer, emergency preemption protocol |
| **Habiba Adel Saleh** | `LaneOrchestrator` FSM implementation, `ConfigLoader` integration, simulation test environment, audit logging system, `pytest` test suite |
| **Salma Mahmoud Abdelhaleem** | Streamlit authority dashboard (frontend + backend), violation model contributions, end-to-end integration testing, performance benchmarking, demo video |

All members participated in planning, code reviews, testing, and final integration.

## References

- Ranftl et al. — *Towards Robust Monocular Depth Estimation* (Intel ISL) — MiDaS foundation paper
- Chen et al. — *Rethinking Atrous Convolution for Semantic Image Segmentation* — DeepLabV3+ foundation paper
- Webster, F. V. — *Traffic Signal Settings*, Road Research Technical Paper No. 39 — signal timing theory
- [Ultralytics YOLOv8 Documentation](https://docs.ultralytics.com) — primary object detection framework
- [PyTorch Documentation](https://pytorch.org/docs)
- [OpenCV Documentation](https://docs.opencv.org)
- [n8n Documentation](https://docs.n8n.io)

## License

This project is licensed under the **Apache License 2.0** — see the [LICENSE](LICENSE) file for details.

---

<p align="center">Built as a graduation project supporting smart city development and road safety in Egypt 🇪🇬</p>
