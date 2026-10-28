# Kelvin6K ATOM Technical Specifications

**Manufacturer / Brand:** Kelvin6k Robotic & Sustainable Concrete Technology Solutions  
**Document Type:** Proprietary Technical Specification  
**Version:** ATOM-V1.0  
**Source Evidence Images:**
- `docs/knowledge/robot_parts/technical_specs/source_images/atom_robot_details_table.png` (Robot Details & Performance Tables)
- `docs/knowledge/robot_parts/technical_specs/source_images/atom_safety_connectivity_table_zoom.png` (Safety, Connectivity, Warranty & Certification Tables)

---

## Overview of ATOM Configurations

The Kelvin6K ATOM concrete 3D-printing robotic system is specified in three distinct configurations:

1. **ATOM – Robot Only:** Fixed pedestal robotic arm for dedicated stationery concrete deposition.
2. **ATOM – Robot + Rover Base:** Robotic arm integrated on an autonomous mobile rover base for flexible positioning across construction job sites.
3. **ATOM – Robot + Linear Axis:** Robotic arm integrated on a synchronized linear track axis for extended linear print envelopes and elongated wall construction.

---

## 1. Robot Details Specification

Source: `atom_robot_details_table.png` (Table Section: Robot Details)

| S.no. | Parameter | Unit | ATOM – Robot Only | ATOM – Robot + Rover Base | ATOM – Robot + Linear Axis |
| :---: | :--- | :---: | :--- | :--- | :--- |
| 1 | Equipment dimensions (L × W × H) meter | meter | 3 × 0.7 × 3 | 3 × 1.2 × 3.5 | 3 × 0.7 × 3.5 |
| 2 | Build Envelop | - | Circular shape | Circular shape | Slot shape |
| 3 | Build Reach | meter | 5.2 × 3 (diameter × height) | 5.2 × 3 (diameter × height) | 2.6 × 2.5 × 3 (slot radius × slot length × height) |
| 4 | Number of axis | axes | 3 | 3 | 4 |
| 5 | Printer weight | kgs | 550kgs | 700kgs | 900kgs |

### Robot Details Notes & Verification
- **Equipment Dimensions:**
  - **ATOM – Robot Only:** 3 × 0.7 × 3 meter (3.0 m Length × 0.7 m Width × 3.0 m Height).
  - **ATOM – Robot + Rover Base:** 3 × 1.2 × 3.5 meter (3.0 m Length × 1.2 m Width × 3.5 m Height). Width increases to 1.2 m to accommodate the mobile rover chassis; height increases to 3.5 m.
  - **ATOM – Robot + Linear Axis:** 3 × 0.7 × 3.5 meter (3.0 m Length × 0.7 m Width × 3.5 m Height). Preserves narrow 0.7 m transport width while overall height reaches 3.5 m.
- **Build Envelope & Reach:**
  - **Robot Only & Rover Base:** Have a **Circular shape** build envelope with cylindrical build reach of **5.2 × 3 (diameter × height)** in meters (5.2 m diameter × 3.0 m height).
  - **Linear Axis:** Has a **Slot shape** build envelope with build reach specified as **2.6 × 2.5 × 3 (slot radius × slot length × height)** in meters (2.6 m slot radius × 2.5 m linear stroke length × 3.0 m height).
- **Number of Axes:**
  - **Robot Only:** 3 axes.
  - **Rover Base:** 3 axes.
  - **Linear Axis:** 4 axes (3 robot arm articulated axes + 1 synchronized linear rail axis).
- **Printer Weight:**
  - **Robot Only:** 550kgs (550 kg).
  - **Rover Base:** 700kgs (700 kg).
  - **Linear Axis:** 900kgs (900 kg).

---

## 2. Performance Specification

Source: `atom_robot_details_table.png` (Table Section: Performance)

| S.no. | Parameter | Unit | ATOM – Robot Only | ATOM – Robot + Rover Base | ATOM – Robot + Linear Axis |
| :---: | :--- | :---: | :--- | :--- | :--- |
| 1 | Position repeatability | mm | 0.1mm | 0.1mm | 0.1mm |
| 2 | Path repeatability | mm | 0.1mm | 0.1mm | 0.1mm |
| 3 | Print material | - | Kelvicrete | Kelvicrete | Kelvicrete |
| 4 | Layer resolution | mm | 20 - 70 mm | 20 - 70 mm | 20 - 70 mm |
| 5 | Print speed | mm/s | upto 200mm/s | upto 200mm/s | upto 200mm/s |
| 6 | Driving speed | km/hr | - | 5km/hr | 5km/hr |
| 7 | Print precision (X / Y / Z)mm | mm | 0.1/0.1/0.1 | 0.1/0.1/0.1 | 0.1/0.1/0.1 |
| 8 | Nozzle diameter (standard) | inch / mm | 1 inch / 25 mm | 1 inch / 25 mm | 1 inch / 25 mm |
| 9 | Nozzle diameter (optional) | inch / mm | 0.75 inch / 20 mm | 0.75 inch / 20 mm | 0.75 inch / 20 mm |

### Performance Notes & Verification
- **Repeatability & Precision:** Position repeatability is 0.1mm, path repeatability is 0.1mm, and print precision across X / Y / Z is 0.1/0.1/0.1 mm across all three configurations.
- **Print Material:** Kelvicrete (Kelvin6K proprietary printable mortar).
- **Layer Resolution:** 20 to 70 mm layer thickness capability.
- **Print Speed:** Up to 200 mm/s ("upto 200mm/s") for all configurations.
- **Driving Speed:** Listed as `-` for ATOM – Robot Only because it is a fixed, non-mobile configuration. Listed as `5km/hr` for ATOM – Robot + Rover Base and `5km/hr` for ATOM – Robot + Linear Axis.
- **Nozzles:** Standard nozzle diameter is 1 inch (25 mm); optional fine nozzle diameter is 0.75 inch (20 mm).

---

## 3. Safety Specification

Source: `atom_safety_connectivity_table_zoom.png` (Table Section: Safety)

| S.no. | Parameter | Unit | ATOM – Robot Only | ATOM – Robot + Rover Base | ATOM – Robot + Linear Axis |
| :---: | :--- | :---: | :--- | :--- | :--- |
| 1 | Double circuits with supervision | - | yes | yes | yes |
| 2 | Emergency stops | - | yes | yes | yes |
| 3 | Safety functions | - | yes | yes | yes |
| 4 | Safety fence | - | Optional | yes | yes |
| 5 | Environment temperature (celsius) | celsius | 0 to 50 | 0 to 50 | 0 to 50 |
| 6 | Humidity (non-condensive) | % | 95% | 95% | 95% |

### Safety Notes & Verification
- **Supervision & E-Stops:** Dual circuits with active supervision, hardwired emergency stops, and integrated safety functions are standard (`yes`) across all configurations.
- **Safety Fence Requirement:**
  - **ATOM – Robot Only:** Listed as **Optional**.
  - **ATOM – Robot + Rover Base:** Listed as **yes** (mandatory safety fence due to autonomous driving rover base).
  - **ATOM – Robot + Linear Axis:** Listed as **yes** (mandatory safety fence due to linear track movement hazard zone).
- **Environmental Limits:** Operating temperature range is 0 to 50 degrees Celsius (`0 to 50 celsius`). Maximum non-condensing relative humidity is 95% (`95%`, listed as `non-condensive` in source).

---

## 4. Connectivity Specification

Source: `atom_safety_connectivity_table_zoom.png` (Table Section: Connectivity)

| S.no. | Parameter | Unit | ATOM – Robot Only | ATOM – Robot + Rover Base | ATOM – Robot + Linear Axis |
| :---: | :--- | :---: | :--- | :--- | :--- |
| 1 | WiFi required for service | - | optional | yes | yes |
| 2 | Stand-alone USB printing | - | yes | yes | yes |
| 3 | Remote support | - | yes | yes | yes |

### Connectivity Notes & Verification
- **WiFi Requirement:** WiFi is **optional** for ATOM – Robot Only, whereas it is **yes** (required) for ATOM – Robot + Rover Base and ATOM – Robot + Linear Axis.
- **Offline / USB & Remote Support:** Stand-alone USB printing without network connection is supported (`yes`) on all three configurations. Remote engineering support is supported (`yes`) on all three configurations.

---

## 5. Warranty & Certification Specification

Source: `atom_safety_connectivity_table_zoom.png` (Table Section: Warranty & Certification)

| S.no. | Parameter | Unit | ATOM – Robot Only | ATOM – Robot + Rover Base | ATOM – Robot + Linear Axis |
| :---: | :--- | :---: | :--- | :--- | :--- |
| 1 | Warranty | months | 12 months | 12 months | 12 months |
| 2 | Certifications | - | yes | yes | yes |

### Warranty & Certification Notes
- Standard warranty period is **12 months** across all three configurations.
- Regulatory and industrial certifications are verified (`yes`) across all configurations.

---

## 6. Detailed Configuration Comparison

### ATOM – Robot Only Profile
- **Base Style:** Fixed Pedestal
- **Dimensions:** 3 × 0.7 × 3 meter (3m L × 0.7m W × 3m H)
- **Build Envelope:** Circular shape
- **Build Reach:** 5.2 × 3 (diameter × height) meter
- **Axes Count:** 3 axes
- **Printer Weight:** 550kgs
- **Safety Fence:** Optional
- **WiFi Service Requirement:** optional
- **Driving Speed:** None / Not applicable (`-`)

### ATOM – Robot + Rover Base Profile
- **Base Style:** Mobile Rover Base
- **Dimensions:** 3 × 1.2 × 3.5 meter (3m L × 1.2m W × 3.5m H)
- **Build Envelope:** Circular shape
- **Build Reach:** 5.2 × 3 (diameter × height) meter
- **Axes Count:** 3 axes
- **Printer Weight:** 700kgs
- **Safety Fence:** yes (required)
- **WiFi Service Requirement:** yes (required)
- **Driving Speed:** 5km/hr

### ATOM – Robot + Linear Axis Profile
- **Base Style:** Linear Rail Track
- **Dimensions:** 3 × 0.7 × 3.5 meter (3m L × 0.7m W × 3.5m H)
- **Build Envelope:** Slot shape
- **Build Reach:** 2.6 × 2.5 × 3 (slot radius × slot length × height) meter
- **Axes Count:** 4 axes
- **Printer Weight:** 900kgs
- **Safety Fence:** yes (required)
- **WiFi Service Requirement:** yes (required)
- **Driving Speed:** 5km/hr

---

## 7. Knowledge Search and Query Reference

### Question 1: How many axes does the ATOM Linear Axis configuration have?
- **Answer:** The ATOM – Robot + Linear Axis configuration has **4 axes** (3 articulated robot arm axes plus 1 synchronized linear track axis). In comparison, the ATOM – Robot Only and ATOM – Robot + Rover Base configurations each have 3 axes.
- **Source:** `atom_robot_details_table.png`, Section: Robot Details, Parameter: Number of axis.

### Question 2: What is the listed printer weight for the Rover Base configuration?
- **Answer:** The listed printer weight for the ATOM – Robot + Rover Base configuration is **700kgs** (700 kg). In comparison, the ATOM – Robot Only configuration weighs 550kgs and the ATOM – Robot + Linear Axis configuration weighs 900kgs.
- **Source:** `atom_robot_details_table.png`, Section: Robot Details, Parameter: Printer weight.

### Question 3: What safety-fence information is listed for Robot Only?
- **Answer:** For the ATOM – Robot Only configuration, the safety fence is listed as **Optional**. In contrast, for both the ATOM – Robot + Rover Base and ATOM – Robot + Linear Axis configurations, the safety fence is mandatory (`yes`).
- **Source:** `atom_safety_connectivity_table_zoom.png`, Section: Safety, Parameter: Safety fence.

### Question 4: Compare the three configurations' equipment dimensions.
- **Answer:** The equipment dimensions (Length × Width × Height in meters) across the three ATOM configurations are:
  - **ATOM – Robot Only:** 3 × 0.7 × 3 meter (3m L × 0.7m W × 3m H).
  - **ATOM – Robot + Rover Base:** 3 × 1.2 × 3.5 meter (3m L × 1.2m W × 3.5m H) — features a wider 1.2m footprint for the rover chassis and reaches 3.5m height.
  - **ATOM – Robot + Linear Axis:** 3 × 0.7 × 3.5 meter (3m L × 0.7m W × 3.5m H) — retains the compact 0.7m width while reaching 3.5m height.
- **Source:** `atom_robot_details_table.png`, Section: Robot Details, Parameter: Equipment dimensions (L × W × H) meter.
