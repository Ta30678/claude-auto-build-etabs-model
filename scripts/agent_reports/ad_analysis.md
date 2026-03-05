# Agent 1: Buildings A & D Analysis Report

## 1. Data Summary

| Item | Building A | Building D | OLD Model |
|------|-----------|-----------|-----------|
| Units | KGF/CM | KGF/CM | TON/M |
| Points | 1007 | 1042 | 917 |
| Column lines | 67 | 65 | 65 |
| Beam lines | 437 | 457 | 379 |
| Frame sections | 598 | 489 | 413 |
| X-Grids | 28 | 28 | 28 |
| Y-Grids | 24 | 24 | 24 |

## 2. Grid Coordinate Comparison

### 2a. A vs OLD (after converting A from CM to M)

  X-Grid 'D': A=-17.8625m vs OLD=-18.6125m (diff=0.7500m)
  X-Grid 'E': A=-16.8125m vs OLD=-16.7625m (diff=0.0500m)
  X-Grid 'F': A=-11.2625m vs OLD=-12.2125m (diff=0.9500m)
  Y-Grid '6': A=19.6500m vs OLD=21.8000m (diff=2.1500m)
  Y-Grid '7': A=21.1500m vs OLD=23.3000m (diff=2.1500m)
  Y-Grid '9': A=42.4550m vs OLD=40.3000m (diff=2.1550m)
  Y-Grid '10': A=43.6800m vs OLD=41.5250m (diff=2.1550m)
  Y-Grid '11': A=45.0050m vs OLD=42.8500m (diff=2.1550m)
  Y-Grid '12': A=45.8050m vs OLD=43.6500m (diff=2.1550m)
  Y-Grid '13': A=49.3300m vs OLD=47.1750m (diff=2.1550m)
  Y-Grid '14': A=52.7050m vs OLD=52.0000m (diff=0.7050m)
  Y-Grid '15': A=53.0550m vs OLD=52.3500m (diff=0.7050m)
  Y-Grid '16': A=54.2050m vs OLD=53.5000m (diff=0.7050m)
  Y-Grid '17': A=59.1550m vs OLD=58.4500m (diff=0.7050m)
  Y-Grid '18': A=61.3439m vs OLD=60.6389m (diff=0.7050m)
  Y-Grid '19': A=62.9300m vs OLD=62.2250m (diff=0.7050m)
  Y-Grid '20': A=64.6550m vs OLD=63.9500m (diff=0.7050m)
  Y-Grid '21': A=76.2050m vs OLD=75.5000m (diff=0.7050m)
  Y-Grid '22': A=81.5300m vs OLD=80.8250m (diff=0.7050m)
  Y-Grid '8-1': A=22.8250m vs OLD=24.9750m (diff=2.1500m)
  Y-Grid '8-2': A=33.4700m vs OLD=32.8000m (diff=0.6700m)
  Y-Grid '8-3': A=34.8700m vs OLD=34.2000m (diff=0.6700m)

### 2b. D vs OLD (after converting D from CM to M)

  X-Grid 'U': D=69.9875m vs OLD=70.5125m (diff=0.5250m)
  X-Grid 'Y': D=79.6875m vs OLD=80.7375m (diff=1.0500m)
  Y-Grid '7': D=22.6250m vs OLD=23.3000m (diff=0.6750m)
  Y-Grid '8-3': D=33.1500m vs OLD=34.2000m (diff=1.0500m)

### 2c. A vs D (both in CM, converted to M)

  X-Grid 'D': A=-17.8625m vs D=-18.6125m (diff=0.7500m)
  X-Grid 'E': A=-16.8125m vs D=-16.7625m (diff=0.0500m)
  X-Grid 'F': A=-11.2625m vs D=-12.2125m (diff=0.9500m)
  X-Grid 'U': A=70.5125m vs D=69.9875m (diff=0.5250m)
  X-Grid 'Y': A=80.7375m vs D=79.6875m (diff=1.0500m)
  Y-Grid '6': A=19.6500m vs D=21.8000m (diff=2.1500m)
  Y-Grid '7': A=21.1500m vs D=22.6250m (diff=1.4750m)
  Y-Grid '9': A=42.4550m vs D=40.3000m (diff=2.1550m)
  Y-Grid '10': A=43.6800m vs D=41.5250m (diff=2.1550m)
  Y-Grid '11': A=45.0050m vs D=42.8500m (diff=2.1550m)
  Y-Grid '12': A=45.8050m vs D=43.6500m (diff=2.1550m)
  Y-Grid '13': A=49.3300m vs D=47.1750m (diff=2.1550m)
  Y-Grid '14': A=52.7050m vs D=52.0000m (diff=0.7050m)
  Y-Grid '15': A=53.0550m vs D=52.3500m (diff=0.7050m)
  Y-Grid '16': A=54.2050m vs D=53.5000m (diff=0.7050m)
  Y-Grid '17': A=59.1550m vs D=58.4500m (diff=0.7050m)
  Y-Grid '18': A=61.3439m vs D=60.6389m (diff=0.7050m)
  Y-Grid '19': A=62.9300m vs D=62.2250m (diff=0.7050m)
  Y-Grid '20': A=64.6550m vs D=63.9500m (diff=0.7050m)
  Y-Grid '21': A=76.2050m vs D=75.5000m (diff=0.7050m)
  Y-Grid '22': A=81.5300m vs D=80.8250m (diff=0.7050m)
  Y-Grid '8-1': A=22.8250m vs D=24.9750m (diff=2.1500m)
  Y-Grid '8-2': A=33.4700m vs D=32.8000m (diff=0.6700m)
  Y-Grid '8-3': A=34.8700m vs D=33.1500m (diff=1.7200m)

## 3. Section Definition Analysis

### 3a. Section Counts by Type

| Type | Building A | Building D | OLD Model |
|------|-----------|-----------|-----------|
| Column (CxxxXxxx) | 69 | 69 | 66 |
| Beam (B/WB/FB/SB/AB) | 78 | 78 | 78 |
| SRC/SRB | 73 | 73 | 73 |
| General (SRC box) | 278 | 170 | 97 |
| Other | 100 | 99 | 99 |

### 3b. Section Name vs Actual Dimension Mismatches

#### Building A

All Rectangular section names match their D/B values.

#### Building D

All Rectangular section names match their D/B values.

#### OLD Model

All Rectangular section names match their D/B values.

### 3c. Sections Unique to Each Model


**Sections in A but NOT in OLD (185):**

- `-1000x1100x40x40C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1100x45x45C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1100x50x50C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1100x55x55C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1100x60x60C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1100x65x65C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1200x60x60C630O` (shape=General, D=100.0, B=120.0 cm)
- `-1000x1200x65x65C630O` (shape=General, D=100.0, B=120.0 cm)
- `-1000x1300x65x65C630O` (shape=General, D=100.0, B=130.0 cm)
- `-1000x1500x65x65C630O` (shape=General, D=100.0, B=150.0 cm)
- `-1000x1700x65x65C630O` (shape=General, D=100.0, B=170.0 cm)
- `-1000x1800x65x65C630O` (shape=General, D=100.0, B=180.0 cm)
- `-1000x1900x65x65C630O` (shape=General, D=100.0, B=190.0 cm)
- `-1000x2000x70x70C630O` (shape=General, D=100.0, B=200.0 cm)
- `-1000x2100x70x70C630O` (shape=General, D=100.0, B=210.0 cm)
- `-1000x2200x70x70C630O` (shape=General, D=100.0, B=220.0 cm)
- `-1000x2300x70x70C630O` (shape=General, D=100.0, B=230.0 cm)
- `-1000x2400x70x70C630O` (shape=General, D=100.0, B=240.0 cm)
- `-1000x2500x70x70C630O` (shape=General, D=100.0, B=250.0 cm)
- `-1000x2600x70x70C630O` (shape=General, D=100.0, B=260.0 cm)
- `-1000x2700x75x75C630O` (shape=General, D=100.0, B=270.0 cm)
- `-1000x2800x75x75C630O` (shape=General, D=100.0, B=280.0 cm)
- `-1000x2900x80x80C630O` (shape=General, D=100.0, B=290.0 cm)
- `-1000x3000x80x80C630O` (shape=General, D=100.0, B=300.0 cm)
- `-1000x3100x85x85C630O` (shape=General, D=100.0, B=310.0 cm)
- `-1000x3200x85x85C630O` (shape=General, D=100.0, B=320.0 cm)
- `-1000x3300x90x90C630O` (shape=General, D=100.0, B=330.0 cm)
- `-1000x3400x90x90C630O` (shape=General, D=100.0, B=340.0 cm)
- `-1000x3500x95x95C630O` (shape=General, D=100.0, B=350.0 cm)
- `-1000x3600x95x95C630O` (shape=General, D=100.0, B=360.0 cm)
- `-1000x3700x100x100C630O` (shape=General, D=100.0, B=370.0 cm)
- `-1000x3800x100x100C630O` (shape=General, D=100.0, B=380.0 cm)
- `-1000x3900x105x105C630O` (shape=General, D=100.0, B=390.0 cm)
- `-1000x4000x105x105C630O` (shape=General, D=100.0, B=400.0 cm)
- `-1000x4100x110x110C630O` (shape=General, D=100.0, B=410.0 cm)
- `-1000x4200x115x115C630O` (shape=General, D=100.0, B=420.0 cm)
- `-1050x1400x65x65C630O` (shape=General, D=105.0, B=140.0 cm)
- `-1100x1100x65x65C630O` (shape=General, D=110.0, B=110.0 cm)
- `-1100x1400x65x65C630O` (shape=General, D=110.0, B=140.0 cm)
- `-1100x1600x65x65C630O` (shape=General, D=110.0, B=160.0 cm)
- `-1100x1650x65x65C630O` (shape=General, D=110.0, B=165.0 cm)
- `-1100x1700x65x65C630O` (shape=General, D=110.0, B=170.0 cm)
- `-1100x1750x65x65C630O` (shape=General, D=110.0, B=175.0 cm)
- `-1100x2800x75x75C630O` (shape=General, D=110.0, B=280.0 cm)
- `-1150x1100x65x65C630O` (shape=General, D=115.0, B=110.0 cm)
- `-1150x1400x65x65C630O` (shape=General, D=115.0, B=140.0 cm)
- `-1200x1100x65x65C630O` (shape=General, D=120.0, B=110.0 cm)
- `-1200x1200x65x65C630O` (shape=General, D=120.0, B=120.0 cm)
- `-1200x1400x65x65C630O` (shape=General, D=120.0, B=140.0 cm)
- `-1200x1600x65x65C630O` (shape=General, D=120.0, B=160.0 cm)
- `-1200x1750x65x65C630O` (shape=General, D=120.0, B=175.0 cm)
- `-1200x1800x65x65C630O` (shape=General, D=120.0, B=180.0 cm)
- `-1200x1850x65x65C630O` (shape=General, D=120.0, B=185.0 cm)
- `-1200x1900x65x65C630O` (shape=General, D=120.0, B=190.0 cm)
- `-1200x2800x75x75C630O` (shape=General, D=120.0, B=280.0 cm)
- `-1250x1100x65x65C630O` (shape=General, D=125.0, B=110.0 cm)
- `-1250x1400x65x65C630O` (shape=General, D=125.0, B=140.0 cm)
- `-1300x1100x65x65C630O` (shape=General, D=130.0, B=110.0 cm)
- `-1300x1300x65x65C630O` (shape=General, D=130.0, B=130.0 cm)
- `-1300x1400x65x65C630O` (shape=General, D=130.0, B=140.0 cm)
- `-1300x1500x65x65C630O` (shape=General, D=130.0, B=150.0 cm)
- `-1300x1600x65x65C630O` (shape=General, D=130.0, B=160.0 cm)
- `-1300x1700x65x65C630O` (shape=General, D=130.0, B=170.0 cm)
- `-1300x1800x65x65C630O` (shape=General, D=130.0, B=180.0 cm)
- `-1300x2800x75x75C630O` (shape=General, D=130.0, B=280.0 cm)
- `-1300x800x65x65C630O` (shape=General, D=130.0, B=80.0 cm)
- `-1350x1100x65x65C630O` (shape=General, D=135.0, B=110.0 cm)
- `-1350x1400x65x65C630O` (shape=General, D=135.0, B=140.0 cm)
- `-1350x800x65x65C630O` (shape=General, D=135.0, B=80.0 cm)
- `-1400x1100x65x65C630O` (shape=General, D=140.0, B=110.0 cm)
- `-1400x1400x65x65C630O` (shape=General, D=140.0, B=140.0 cm)
- `-1400x1600x65x65C630O` (shape=General, D=140.0, B=160.0 cm)
- `-1400x2800x75x75C630O` (shape=General, D=140.0, B=280.0 cm)
- `-1400x800x65x65C630O` (shape=General, D=140.0, B=80.0 cm)
- `-1450x1100x65x65C630O` (shape=General, D=145.0, B=110.0 cm)
- `-1450x800x65x65C630O` (shape=General, D=145.0, B=80.0 cm)
- `-1500x1100x65x65C630O` (shape=General, D=150.0, B=110.0 cm)
- `-1500x1500x65x65C630O` (shape=General, D=150.0, B=150.0 cm)
- `-1500x1600x65x65C630O` (shape=General, D=150.0, B=160.0 cm)
- `-1500x2800x75x75C630O` (shape=General, D=150.0, B=280.0 cm)
- `-1500x800x65x65C630O` (shape=General, D=150.0, B=80.0 cm)
- `-1550x1100x65x65C630O` (shape=General, D=155.0, B=110.0 cm)
- `-1550x800x65x65C630O` (shape=General, D=155.0, B=80.0 cm)
- `-1600x1600x65x65C630O` (shape=General, D=160.0, B=160.0 cm)
- `-1600x2800x75x75C630O` (shape=General, D=160.0, B=280.0 cm)
- `-1600x800x65x65C630O` (shape=General, D=160.0, B=80.0 cm)
- `-1700x1600x65x65C630O` (shape=General, D=170.0, B=160.0 cm)
- `-1700x1700x65x65C630O` (shape=General, D=170.0, B=170.0 cm)
- `-1800x1600x65x65C630O` (shape=General, D=180.0, B=160.0 cm)
- `-1800x1800x65x65C630O` (shape=General, D=180.0, B=180.0 cm)
- `-1900x1600x65x65C630O` (shape=General, D=190.0, B=160.0 cm)
- `-1900x1900x65x65C630O` (shape=General, D=190.0, B=190.0 cm)
- `-2000x1600x65x65C630O` (shape=General, D=200.0, B=160.0 cm)
- `-2000x2000x65x65C630O` (shape=General, D=200.0, B=200.0 cm)
- `-2000x650x55x55C630O` (shape=General, D=200.0, B=65.0 cm)
- `-2000x650x65x65C630O` (shape=General, D=200.0, B=65.0 cm)
- `-2000x700x55x55C630O` (shape=General, D=200.0, B=70.0 cm)
- `-2000x700x65x65C630O` (shape=General, D=200.0, B=70.0 cm)
- `-2050x700x55x55C630O` (shape=General, D=205.0, B=70.0 cm)
- `-2050x700x65x65C630O` (shape=General, D=205.0, B=70.0 cm)
- `-2100x1000x60x60C630O` (shape=General, D=210.0, B=100.0 cm)
- `-2100x1000x65x65C630O` (shape=General, D=210.0, B=100.0 cm)
- `-2100x1100x65x65C630O` (shape=General, D=210.0, B=110.0 cm)
- `-2100x1200x65x65C630O` (shape=General, D=210.0, B=120.0 cm)
- `-2100x1300x65x65C630O` (shape=General, D=210.0, B=130.0 cm)
- `-2100x1400x65x65C630O` (shape=General, D=210.0, B=140.0 cm)
- `-2100x1500x65x65C630O` (shape=General, D=210.0, B=150.0 cm)
- `-2100x1600x65x65C630O` (shape=General, D=210.0, B=160.0 cm)
- `-2100x1700x65x65C630O` (shape=General, D=210.0, B=170.0 cm)
- `-2100x700x60x60C630O` (shape=General, D=210.0, B=70.0 cm)
- `-2100x700x65x65C630O` (shape=General, D=210.0, B=70.0 cm)
- `-2100x800x60x60C630O` (shape=General, D=210.0, B=80.0 cm)
- `-2100x800x65x65C630O` (shape=General, D=210.0, B=80.0 cm)
- `-2100x900x60x60C630O` (shape=General, D=210.0, B=90.0 cm)
- `-2100x900x65x65C630O` (shape=General, D=210.0, B=90.0 cm)
- `-2150x1000x60x60C630O` (shape=General, D=215.0, B=100.0 cm)
- `-2150x800x65x65C630O` (shape=General, D=215.0, B=80.0 cm)
- `-2200x1000x60x60C630O` (shape=General, D=220.0, B=100.0 cm)
- `-2200x1600x65x65C630O` (shape=General, D=220.0, B=160.0 cm)
- `-2200x800x65x65C630O` (shape=General, D=220.0, B=80.0 cm)
- `-2200x900x65x65C630O` (shape=General, D=220.0, B=90.0 cm)
- `-2250x1000x60x60C630O` (shape=General, D=225.0, B=100.0 cm)
- `-2250x900x65x65C630O` (shape=General, D=225.0, B=90.0 cm)
- `-2300x1000x65x65C630O` (shape=General, D=230.0, B=100.0 cm)
- `-2300x1600x65x65C630O` (shape=General, D=230.0, B=160.0 cm)
- `-2300x900x65x65C630O` (shape=General, D=230.0, B=90.0 cm)
- `-2350x1000x65x65C630O` (shape=General, D=235.0, B=100.0 cm)
- `-2400x1000x65x65C630O` (shape=General, D=240.0, B=100.0 cm)
- `-2400x1600x65x65C630O` (shape=General, D=240.0, B=160.0 cm)
- `-2450x1000x65x65C630O` (shape=General, D=245.0, B=100.0 cm)
- `-2500x1000x70x70C630O` (shape=General, D=250.0, B=100.0 cm)
- `-2500x1600x70x70C630O` (shape=General, D=250.0, B=160.0 cm)
- `-2550x1000x70x70C630O` (shape=General, D=255.0, B=100.0 cm)
- `-2600x1000x70x70C630O` (shape=General, D=260.0, B=100.0 cm)
- `-2600x1600x70x70C630O` (shape=General, D=260.0, B=160.0 cm)
- `-2650x1000x70x70C630O` (shape=General, D=265.0, B=100.0 cm)
- `-2700x1000x75x75C630O` (shape=General, D=270.0, B=100.0 cm)
- `-2750x1000x75x75C630O` (shape=General, D=275.0, B=100.0 cm)
- `-2800x1000x75x75C630O` (shape=General, D=280.0, B=100.0 cm)
- `-2850x1000x75x75C630O` (shape=General, D=285.0, B=100.0 cm)
- `-2900x1000x80x80C630O` (shape=General, D=290.0, B=100.0 cm)
- `-2950x1000x80x80C630O` (shape=General, D=295.0, B=100.0 cm)
- `-3000x1000x80x80C630O` (shape=General, D=300.0, B=100.0 cm)
- `-3100x1000x85x85C630O` (shape=General, D=310.0, B=100.0 cm)
- `-3200x1000x85x85C630O` (shape=General, D=320.0, B=100.0 cm)
- `-3300x1000x90x90C630O` (shape=General, D=330.0, B=100.0 cm)
- `-3400x1000x90x90C630O` (shape=General, D=340.0, B=100.0 cm)
- `-3500x1000x95x95C630O` (shape=General, D=350.0, B=100.0 cm)
- `-3600x1000x95x95C630O` (shape=General, D=360.0, B=100.0 cm)
- `-3700x1000x100x100C630O` (shape=General, D=370.0, B=100.0 cm)
- `-3800x1000x100x100C630O` (shape=General, D=380.0, B=100.0 cm)
- `-3900x1000x105x105C630O` (shape=General, D=390.0, B=100.0 cm)
- `-4000x1000x105x105C630O` (shape=General, D=400.0, B=100.0 cm)
- `-4000x1100x105x105C630O` (shape=General, D=400.0, B=110.0 cm)
- `-4000x1200x105x105C630O` (shape=General, D=400.0, B=120.0 cm)
- `-4000x1300x105x105C630O` (shape=General, D=400.0, B=130.0 cm)
- `-4000x1400x105x105C630O` (shape=General, D=400.0, B=140.0 cm)
- `-4000x1500x105x105C630O` (shape=General, D=400.0, B=150.0 cm)
- `-4000x1600x105x105C630O` (shape=General, D=400.0, B=160.0 cm)
- `-4000x1700x105x105C630O` (shape=General, D=400.0, B=170.0 cm)
- `-4000x1800x105x105C630O` (shape=General, D=400.0, B=180.0 cm)
- `-4000x1900x105x105C630O` (shape=General, D=400.0, B=190.0 cm)
- `-4000x2000x105x105C630O` (shape=General, D=400.0, B=200.0 cm)
- `-700x2100x65x65C630O` (shape=General, D=70.0, B=210.0 cm)
- `-700x2150x65x65C630O` (shape=General, D=70.0, B=215.0 cm)
- `-700x2200x65x65C630O` (shape=General, D=70.0, B=220.0 cm)
- `-700x2250x65x65C630O` (shape=General, D=70.0, B=225.0 cm)
- `-700x2300x65x65C630O` (shape=General, D=70.0, B=230.0 cm)
- `-700x2350x65x65C630O` (shape=General, D=70.0, B=235.0 cm)
- `-700x2400x65x65C630O` (shape=General, D=70.0, B=240.0 cm)
- `-800x2400x65x65C630O` (shape=General, D=80.0, B=240.0 cm)
- `-800x2450x70x70C630O` (shape=General, D=80.0, B=245.0 cm)
- `-800x2500x70x70C630O` (shape=General, D=80.0, B=250.0 cm)
- `-900x2500x70x70C630O` (shape=General, D=90.0, B=250.0 cm)
- `-900x2550x70x70C630O` (shape=General, D=90.0, B=255.0 cm)
- `-900x2600x75x75C630O` (shape=General, D=90.0, B=260.0 cm)
- `-900x2650x75x75C630O` (shape=General, D=90.0, B=265.0 cm)
- `-900x2700x75x75C630O` (shape=General, D=90.0, B=270.0 cm)
- `-900x2750x75x75C630O` (shape=General, D=90.0, B=275.0 cm)
- `-900x2800x75x75C630O` (shape=General, D=90.0, B=280.0 cm)
- `-950x1550x45x45C630O` (shape=General, D=95.0, B=155.0 cm)
- `C100X100C42` (shape=Rectangular, D=100.0, B=100.0 cm)
- `C130X130C42` (shape=Rectangular, D=130.0, B=130.0 cm)
- `C150X150C42` (shape=Rectangular, D=150.0, B=150.0 cm)
- `FSEC1` (shape=Rectangular, D=50.0, B=30.0 cm)


**Sections in D but NOT in OLD (76):**

- `-1000x1100x40x40C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1100x45x45C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1100x50x50C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1100x55x55C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1100x60x60C630O` (shape=General, D=100.0, B=110.0 cm)
- `-1000x1200x60x60C630O` (shape=General, D=100.0, B=120.0 cm)
- `-1000x1200x65x65C630O` (shape=General, D=100.0, B=120.0 cm)
- `-1050x1400x65x65C630O` (shape=General, D=105.0, B=140.0 cm)
- `-1100x1100x65x65C630O` (shape=General, D=110.0, B=110.0 cm)
- `-1100x1400x65x65C630O` (shape=General, D=110.0, B=140.0 cm)
- `-1100x1600x65x65C630O` (shape=General, D=110.0, B=160.0 cm)
- `-1100x1650x65x65C630O` (shape=General, D=110.0, B=165.0 cm)
- `-1100x1700x65x65C630O` (shape=General, D=110.0, B=170.0 cm)
- `-1100x1750x65x65C630O` (shape=General, D=110.0, B=175.0 cm)
- `-1150x1100x65x65C630O` (shape=General, D=115.0, B=110.0 cm)
- `-1150x1400x65x65C630O` (shape=General, D=115.0, B=140.0 cm)
- `-1200x1100x65x65C630O` (shape=General, D=120.0, B=110.0 cm)
- `-1200x1200x65x65C630O` (shape=General, D=120.0, B=120.0 cm)
- `-1200x1400x65x65C630O` (shape=General, D=120.0, B=140.0 cm)
- `-1200x1750x65x65C630O` (shape=General, D=120.0, B=175.0 cm)
- `-1200x1800x65x65C630O` (shape=General, D=120.0, B=180.0 cm)
- `-1200x1850x65x65C630O` (shape=General, D=120.0, B=185.0 cm)
- `-1200x1900x65x65C630O` (shape=General, D=120.0, B=190.0 cm)
- `-1250x1100x65x65C630O` (shape=General, D=125.0, B=110.0 cm)
- `-1250x1400x65x65C630O` (shape=General, D=125.0, B=140.0 cm)
- `-1300x1100x65x65C630O` (shape=General, D=130.0, B=110.0 cm)
- `-1300x1300x65x65C630O` (shape=General, D=130.0, B=130.0 cm)
- `-1300x1400x65x65C630O` (shape=General, D=130.0, B=140.0 cm)
- `-1300x800x65x65C630O` (shape=General, D=130.0, B=80.0 cm)
- `-1350x1100x65x65C630O` (shape=General, D=135.0, B=110.0 cm)
- `-1350x1400x65x65C630O` (shape=General, D=135.0, B=140.0 cm)
- `-1350x800x65x65C630O` (shape=General, D=135.0, B=80.0 cm)
- `-1400x1100x65x65C630O` (shape=General, D=140.0, B=110.0 cm)
- `-1400x1400x65x65C630O` (shape=General, D=140.0, B=140.0 cm)
- `-1400x800x65x65C630O` (shape=General, D=140.0, B=80.0 cm)
- `-1450x1100x65x65C630O` (shape=General, D=145.0, B=110.0 cm)
- `-1450x800x65x65C630O` (shape=General, D=145.0, B=80.0 cm)
- `-1500x1100x65x65C630O` (shape=General, D=150.0, B=110.0 cm)
- `-1500x800x65x65C630O` (shape=General, D=150.0, B=80.0 cm)
- `-1550x1100x65x65C630O` (shape=General, D=155.0, B=110.0 cm)
- `-1550x800x65x65C630O` (shape=General, D=155.0, B=80.0 cm)
- `-1600x800x65x65C630O` (shape=General, D=160.0, B=80.0 cm)
- `-2000x650x65x65C630O` (shape=General, D=200.0, B=65.0 cm)
- `-2000x700x65x65C630O` (shape=General, D=200.0, B=70.0 cm)
- `-2050x700x65x65C630O` (shape=General, D=205.0, B=70.0 cm)
- `-2100x700x65x65C630O` (shape=General, D=210.0, B=70.0 cm)
- `-2100x800x65x65C630O` (shape=General, D=210.0, B=80.0 cm)
- `-2150x800x65x65C630O` (shape=General, D=215.0, B=80.0 cm)
- `-2200x800x65x65C630O` (shape=General, D=220.0, B=80.0 cm)
- `-2200x900x65x65C630O` (shape=General, D=220.0, B=90.0 cm)
- `-2250x900x65x65C630O` (shape=General, D=225.0, B=90.0 cm)
- `-2300x1000x65x65C630O` (shape=General, D=230.0, B=100.0 cm)
- `-2300x900x65x65C630O` (shape=General, D=230.0, B=90.0 cm)
- `-2350x1000x65x65C630O` (shape=General, D=235.0, B=100.0 cm)
- `-2400x1000x65x65C630O` (shape=General, D=240.0, B=100.0 cm)
- `-700x2100x65x65C630O` (shape=General, D=70.0, B=210.0 cm)
- `-700x2150x65x65C630O` (shape=General, D=70.0, B=215.0 cm)
- `-700x2200x65x65C630O` (shape=General, D=70.0, B=220.0 cm)
- `-700x2250x65x65C630O` (shape=General, D=70.0, B=225.0 cm)
- `-700x2300x65x65C630O` (shape=General, D=70.0, B=230.0 cm)
- `-700x2350x65x65C630O` (shape=General, D=70.0, B=235.0 cm)
- `-700x2400x65x65C630O` (shape=General, D=70.0, B=240.0 cm)
- `-800x2400x65x65C630O` (shape=General, D=80.0, B=240.0 cm)
- `-800x2450x70x70C630O` (shape=General, D=80.0, B=245.0 cm)
- `-800x2500x70x70C630O` (shape=General, D=80.0, B=250.0 cm)
- `-900x2500x70x70C630O` (shape=General, D=90.0, B=250.0 cm)
- `-900x2550x70x70C630O` (shape=General, D=90.0, B=255.0 cm)
- `-900x2600x75x75C630O` (shape=General, D=90.0, B=260.0 cm)
- `-900x2650x75x75C630O` (shape=General, D=90.0, B=265.0 cm)
- `-900x2700x75x75C630O` (shape=General, D=90.0, B=270.0 cm)
- `-900x2750x75x75C630O` (shape=General, D=90.0, B=275.0 cm)
- `-900x2800x75x75C630O` (shape=General, D=90.0, B=280.0 cm)
- `-950x1550x45x45C630O` (shape=General, D=95.0, B=155.0 cm)
- `C100X100C420SD490` (shape=Rectangular, D=100.0, B=100.0 cm)
- `C130X130C420SD490` (shape=Rectangular, D=130.0, B=130.0 cm)
- `C150X150C420SD490` (shape=Rectangular, D=150.0, B=150.0 cm)


**Sections in OLD but NOT in A or D (0):**


### 3d. Sections Shared Between A and D with Different Dimensions

All shared sections have identical dimensions.

### 3e. Sections Shared Between A and OLD with Different Dimensions (converted to CM)

All shared sections have matching dimensions.

## 4. Column Connectivity Analysis

### 4a. Column Line Summary

| Category | Count |
|----------|-------|
| Total column lines in A | 67 |
| Total column lines in D | 65 |
| Total column lines in OLD | 65 |
| Common to all three | 65 |
| In A but not OLD | 2 |
| In D but not OLD | 0 |
| In OLD but not A | 0 |
| In OLD but not D | 0 |

### 4b. Column Coordinate Mismatches (A vs OLD, >1cm)

| Column | A_X(m) | A_Y(m) | OLD_X(m) | OLD_Y(m) | dX(m) | dY(m) |
|--------|--------|--------|----------|----------|-------|-------|
| C1 | 49.0875 | 76.2050 | 49.0876 | 75.5000 | 0.0001 | 0.7050 |
| C123 | 15.4625 | 76.2050 | 15.4625 | 75.5000 | 0.0000 | 0.7050 |
| C133 | 5.1125 | 22.8250 | 5.1125 | 24.9750 | 0.0000 | 2.1500 |
| C135 | 5.1125 | 34.8700 | 5.1125 | 34.2000 | 0.0000 | 0.6700 |
| C151 | 4.6625 | 45.8050 | 4.6625 | 43.6500 | 0.0000 | 2.1550 |
| C152 | 4.6625 | 52.7050 | 4.6625 | 52.0000 | 0.0000 | 0.7050 |
| C153 | 4.6625 | 64.6550 | 4.6625 | 63.9500 | 0.0000 | 0.7050 |
| C155 | -3.3875 | 19.6500 | -3.3875 | 21.8000 | 0.0000 | 2.1500 |
| C156 | -3.3875 | 33.4700 | -3.3875 | 32.8000 | 0.0000 | 0.6700 |
| C157 | -3.3875 | 45.0050 | -3.3875 | 42.8500 | 0.0000 | 2.1550 |
| C158 | -3.3875 | 53.0550 | -3.3875 | 52.3500 | 0.0000 | 0.7050 |
| C159 | -3.3875 | 64.6550 | -3.3875 | 63.9500 | 0.0000 | 0.7050 |
| C160 | -11.2625 | 11.6000 | -12.2125 | 11.6000 | 0.9500 | 0.0000 |
| C161 | -11.2625 | 53.0550 | -12.2125 | 52.3500 | 0.9500 | 0.7050 |
| C162 | -11.2625 | 64.6550 | -12.2125 | 63.9500 | 0.9500 | 0.7050 |
| C164 | -16.8125 | 19.6500 | -16.7625 | 21.8000 | 0.0500 | 2.1500 |
| C165 | -16.8125 | 33.4700 | -16.7625 | 32.8000 | 0.0500 | 0.6700 |
| C166 | -16.8125 | 45.0050 | -16.7625 | 42.8500 | 0.0500 | 2.1550 |
| C167 | -17.8625 | 53.0550 | -18.6125 | 52.3500 | 0.7500 | 0.7050 |
| C168 | -17.8625 | 64.6550 | -18.6125 | 63.9500 | 0.7500 | 0.7050 |
| C169 | -17.8625 | 11.6000 | -18.6125 | 11.6000 | 0.7500 | 0.0000 |
| C171 | -28.3375 | 19.6500 | -28.3375 | 21.8000 | 0.0000 | 2.1500 |
| C172 | -28.3375 | 34.8700 | -28.3375 | 34.2000 | 0.0000 | 0.6700 |
| C173 | -28.3375 | 45.0050 | -28.3375 | 42.8500 | 0.0000 | 2.1550 |
| C174 | -28.3375 | 53.0550 | -28.3375 | 52.3500 | 0.0000 | 0.7050 |
| C25 | 80.7375 | 21.1500 | 80.7375 | 23.3000 | 0.0000 | 2.1500 |
| C26 | 80.7375 | 34.8700 | 80.7375 | 34.2000 | 0.0000 | 0.6700 |
| C28 | 68.7625 | 21.1500 | 68.7625 | 23.3000 | 0.0000 | 2.1500 |
| C29 | 70.5125 | 34.8700 | 70.5125 | 34.2000 | 0.0000 | 0.6700 |
| C30 | 68.7625 | 43.6800 | 68.7625 | 41.5250 | 0.0000 | 2.1550 |
| C32 | 60.2875 | 21.1500 | 60.2875 | 23.3000 | 0.0000 | 2.1500 |
| C33 | 60.2875 | 34.8700 | 60.2875 | 34.2000 | 0.0000 | 0.6700 |
| C34 | 60.7625 | 43.6800 | 60.7625 | 41.5250 | 0.0000 | 2.1550 |
| C36 | 49.0875 | 21.1500 | 49.0875 | 23.3000 | 0.0000 | 2.1500 |
| C37 | 49.0875 | 34.8700 | 49.0875 | 34.2000 | 0.0000 | 0.6700 |
| C38 | 48.7875 | 43.6800 | 48.7875 | 41.5250 | 0.0000 | 2.1550 |
| C39 | 49.0875 | 54.2050 | 49.0875 | 53.5000 | 0.0000 | 0.7050 |
| C40 | 49.0875 | 64.6550 | 49.0876 | 63.9500 | 0.0001 | 0.7050 |
| C42 | 38.1125 | 22.8250 | 38.1125 | 24.9750 | 0.0000 | 2.1500 |
| C43 | 38.1125 | 34.8700 | 38.1125 | 34.2000 | 0.0000 | 0.6700 |
| C46 | 38.1125 | 45.0050 | 38.1125 | 42.8500 | 0.0000 | 2.1550 |
| C47 | 38.1125 | 54.2050 | 38.1125 | 53.5000 | 0.0000 | 0.7050 |
| C48 | 38.1125 | 62.9300 | 38.1125 | 62.2250 | 0.0000 | 0.7050 |
| C53 | 38.4625 | 76.2050 | 38.4625 | 75.5000 | 0.0000 | 0.7050 |
| C58 | 26.9125 | 22.8250 | 26.9125 | 24.9750 | 0.0000 | 2.1500 |
| C60 | 26.9125 | 34.8700 | 26.9125 | 34.2000 | 0.0000 | 0.6700 |
| C61 | 27.6625 | 45.0050 | 27.6625 | 42.8500 | 0.0000 | 2.1550 |
| C64 | 26.9125 | 54.2050 | 26.9125 | 53.5000 | 0.0000 | 0.7050 |
| C65 | 26.9125 | 62.9300 | 26.9125 | 62.2250 | 0.0000 | 0.7050 |
| C69 | 26.9125 | 76.2050 | 26.9125 | 75.5000 | 0.0000 | 0.7050 |
| C80 | 16.2875 | 21.1500 | 16.2875 | 23.3000 | 0.0000 | 2.1500 |
| C83 | 16.2875 | 34.8700 | 16.2875 | 34.2000 | 0.0000 | 0.6700 |
| C85 | 15.4625 | 45.8050 | 15.4625 | 43.6500 | 0.0000 | 2.1550 |
| C89 | 15.4625 | 64.6550 | 15.4625 | 63.9500 | 0.0000 | 0.7050 |

### 4c. Column Coordinate Mismatches (D vs OLD, >1cm)

| Column | D_X(m) | D_Y(m) | OLD_X(m) | OLD_Y(m) | dX(m) | dY(m) |
|--------|--------|--------|----------|----------|-------|-------|
| C135 | 5.1125 | 33.1500 | 5.1125 | 34.2000 | 0.0000 | 1.0500 |
| C172 | -28.3375 | 33.1500 | -28.3375 | 34.2000 | 0.0000 | 1.0500 |
| C24 | 79.6875 | 11.6000 | 80.7375 | 11.6000 | 1.0500 | 0.0000 |
| C25 | 79.6875 | 22.6250 | 80.7375 | 23.3000 | 1.0500 | 0.6750 |
| C26 | 79.6875 | 33.1500 | 80.7375 | 34.2000 | 1.0500 | 1.0500 |
| C27 | 69.9875 | 11.6000 | 70.5125 | 11.6000 | 0.5250 | 0.0000 |
| C28 | 68.7625 | 22.6250 | 68.7625 | 23.3000 | 0.0000 | 0.6750 |
| C29 | 69.9875 | 33.1500 | 70.5125 | 34.2000 | 0.5250 | 1.0500 |
| C32 | 60.2875 | 22.6250 | 60.2875 | 23.3000 | 0.0000 | 0.6750 |
| C33 | 60.2875 | 33.1500 | 60.2875 | 34.2000 | 0.0000 | 1.0500 |
| C36 | 49.0875 | 22.6250 | 49.0875 | 23.3000 | 0.0000 | 0.6750 |
| C37 | 49.0875 | 33.1500 | 49.0875 | 34.2000 | 0.0000 | 1.0500 |
| C43 | 38.1125 | 33.1500 | 38.1125 | 34.2000 | 0.0000 | 1.0500 |
| C60 | 26.9125 | 33.1500 | 26.9125 | 34.2000 | 0.0000 | 1.0500 |
| C80 | 16.2875 | 22.6250 | 16.2875 | 23.3000 | 0.0000 | 0.6750 |
| C83 | 16.2875 | 33.1500 | 16.2875 | 34.2000 | 0.0000 | 1.0500 |

### 4d. Building-Specific Columns (Above Ground)

| Category | Count |
|----------|-------|
| A-only above-ground columns | 2 |
| D-only above-ground columns | 0 |
| Shared above-ground columns (both A and D) | 65 |
| OLD basement columns (B6F-1F) | 65 |
| A columns missing from OLD | 2 |
| D columns missing from OLD | 0 |

**A columns with NO matching OLD basement column:** ['C2', 'C3']

## 5. Column Section Assignments at Transition Stories

### Key: 1F is the connection level between basement (OLD) and superstructure (A/D)


#### Story: B1F

Columns assigned: A=67, D=65, OLD=65

**D vs OLD section differences (9):**

| Column | D Section | OLD Section |
|--------|-----------|-------------|
| C24 | C150X150C420SD490 | C120X120C56SD490 |
| C25 | C150X150C420SD490 | C120X160C560SD490 |
| C26 | C150X150C420SD490 | C120X120C56SD490 |
| C27 | C150X150C420SD490 | C120X120C56SD490 |
| C28 | C150X150C420SD490 | C135X110C560SD490 |
| C29 | C150X150C420SD490 | C120X120C56SD490 |
| C31 | C150X150C420SD490 | C120X120C28SD490 |
| C32 | C150X150C420SD490 | C120X120C56SD490 |
| C33 | C150X150C420SD490 | C120X120C56SD490 |

**A vs D section differences (9):**

| Column | A Section | D Section |
|--------|-----------|-----------|
| C24 | C120X120C56SD490 | C150X150C420SD490 |
| C25 | C120X160C560SD490 | C150X150C420SD490 |
| C26 | C120X120C56SD490 | C150X150C420SD490 |
| C27 | C120X120C56SD490 | C150X150C420SD490 |
| C28 | C135X110C560SD490 | C150X150C420SD490 |
| C29 | C120X120C56SD490 | C150X150C420SD490 |
| C31 | C120X120C28SD490 | C150X150C420SD490 |
| C32 | C120X120C56SD490 | C150X150C420SD490 |
| C33 | C120X120C56SD490 | C150X150C420SD490 |


#### Story: 1F

Columns assigned: A=67, D=65, OLD=65

**D vs OLD section differences (9):**

| Column | D Section | OLD Section |
|--------|-----------|-------------|
| C24 | C150X150C420SD490 | C120X120C56SD490 |
| C25 | C150X150C420SD490 | C120X160C560SD490 |
| C26 | C150X150C420SD490 | C120X120C56SD490 |
| C27 | C150X150C420SD490 | C120X120C56SD490 |
| C28 | C150X150C420SD490 | C135X110C560SD490 |
| C29 | C150X150C420SD490 | C120X120C56SD490 |
| C31 | C150X150C420SD490 | C120X120C28SD490 |
| C32 | C150X150C420SD490 | C120X120C56SD490 |
| C33 | C150X150C420SD490 | C120X120C56SD490 |

**A vs D section differences (9):**

| Column | A Section | D Section |
|--------|-----------|-----------|
| C24 | C120X120C56SD490 | C150X150C420SD490 |
| C25 | C120X160C560SD490 | C150X150C420SD490 |
| C26 | C120X120C56SD490 | C150X150C420SD490 |
| C27 | C120X120C56SD490 | C150X150C420SD490 |
| C28 | C135X110C560SD490 | C150X150C420SD490 |
| C29 | C120X120C56SD490 | C150X150C420SD490 |
| C31 | C120X120C28SD490 | C150X150C420SD490 |
| C32 | C120X120C56SD490 | C150X150C420SD490 |
| C33 | C120X120C56SD490 | C150X150C420SD490 |


#### Story: 1MF

Columns assigned: A=17, D=9, OLD=0


#### Story: 2F

Columns assigned: A=17, D=9, OLD=0


#### Story: 3F

Columns assigned: A=17, D=9, OLD=0

## 6. Column Connectivity Detail Table (at 1F level)

Shows column positions and section assignments for A, D, and OLD at transition stories.

| Col | A_X(m) | A_Y(m) | OLD_X(m) | OLD_Y(m) | dX(cm) | dY(cm) | A_sec@1F | D_sec@1F | OLD_sec@1F | Match? |
|-----|--------|--------|----------|----------|--------|--------|----------|----------|------------|--------|
| C1 | 49.0875 | 76.2050 | 49.0876 | 75.5000 | 0.0 | 70.5 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | MISMATCH |
| C2 | -16.8125 | 34.8700 | N/A | N/A | N/A | N/A | C150X150C42 | - | - | N/A |
| C3 | -3.3875 | 34.8700 | N/A | N/A | N/A | N/A | C150X150C42 | - | - | N/A |
| C24 | 80.7375 | 11.6000 | 80.7375 | 11.6000 | 0.0 | 0.0 | C120X120C56SD490 | C150X150C420SD490 | C120X120C56SD490 | OK |
| C25 | 80.7375 | 21.1500 | 80.7375 | 23.3000 | 0.0 | 215.0 | C120X160C560SD490 | C150X150C420SD490 | C120X160C560SD490 | MISMATCH |
| C26 | 80.7375 | 34.8700 | 80.7375 | 34.2000 | 0.0 | 67.0 | C120X120C56SD490 | C150X150C420SD490 | C120X120C56SD490 | MISMATCH |
| C27 | 70.5125 | 11.6000 | 70.5125 | 11.6000 | 0.0 | 0.0 | C120X120C56SD490 | C150X150C420SD490 | C120X120C56SD490 | OK |
| C28 | 68.7625 | 21.1500 | 68.7625 | 23.3000 | 0.0 | 215.0 | C135X110C560SD490 | C150X150C420SD490 | C135X110C560SD490 | MISMATCH |
| C29 | 70.5125 | 34.8700 | 70.5125 | 34.2000 | 0.0 | 67.0 | C120X120C56SD490 | C150X150C420SD490 | C120X120C56SD490 | MISMATCH |
| C30 | 68.7625 | 43.6800 | 68.7625 | 41.5250 | 0.0 | 215.5 | C70X70C56SD490 | C70X70C56SD490 | C70X70C56SD490 | MISMATCH |
| C31 | 60.2875 | 11.6000 | 60.2875 | 11.6000 | 0.0 | 0.0 | C120X120C28SD490 | C150X150C420SD490 | C120X120C28SD490 | OK |
| C32 | 60.2875 | 21.1500 | 60.2875 | 23.3000 | 0.0 | 215.0 | C120X120C56SD490 | C150X150C420SD490 | C120X120C56SD490 | MISMATCH |
| C33 | 60.2875 | 34.8700 | 60.2875 | 34.2000 | 0.0 | 67.0 | C120X120C56SD490 | C150X150C420SD490 | C120X120C56SD490 | MISMATCH |
| C34 | 60.7625 | 43.6800 | 60.7625 | 41.5250 | 0.0 | 215.5 | C70X70C56SD490 | C70X70C56SD490 | C70X70C56SD490 | MISMATCH |
| C35 | 49.0875 | 11.6000 | 49.0875 | 11.6000 | 0.0 | 0.0 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | OK |
| C36 | 49.0875 | 21.1500 | 49.0875 | 23.3000 | 0.0 | 215.0 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C37 | 49.0875 | 34.8700 | 49.0875 | 34.2000 | 0.0 | 67.0 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C38 | 48.7875 | 43.6800 | 48.7875 | 41.5250 | 0.0 | 215.5 | C70X70C56SD490 | C70X70C56SD490 | C70X70C56SD490 | MISMATCH |
| C39 | 49.0875 | 54.2050 | 49.0875 | 53.5000 | 0.0 | 70.5 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C40 | 49.0875 | 64.6550 | 49.0876 | 63.9500 | 0.0 | 70.5 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | MISMATCH |
| C41 | 38.4625 | 11.6000 | 38.4625 | 11.6000 | 0.0 | 0.0 | C120X180C280SD490 | C120X180C280SD490 | C120X180C280SD490 | OK |
| C42 | 38.1125 | 22.8250 | 38.1125 | 24.9750 | 0.0 | 215.0 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C43 | 38.1125 | 34.8700 | 38.1125 | 34.2000 | 0.0 | 67.0 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C46 | 38.1125 | 45.0050 | 38.1125 | 42.8500 | 0.0 | 215.5 | C70X70C56SD490 | C70X70C56SD490 | C70X70C56SD490 | MISMATCH |
| C47 | 38.1125 | 54.2050 | 38.1125 | 53.5000 | 0.0 | 70.5 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C48 | 38.1125 | 62.9300 | 38.1125 | 62.2250 | 0.0 | 70.5 | C145X100C560SD490 | C145X100C560SD490 | C145X100C560SD490 | MISMATCH |
| C53 | 38.4625 | 76.2050 | 38.4625 | 75.5000 | 0.0 | 70.5 | C120X180C280SD490 | C120X180C280SD490 | C120X180C280SD490 | MISMATCH |
| C54 | 26.9125 | 11.6000 | 26.9125 | 11.6000 | 0.0 | 0.0 | C120X180C280SD490 | C120X180C280SD490 | C120X180C280SD490 | OK |
| C58 | 26.9125 | 22.8250 | 26.9125 | 24.9750 | 0.0 | 215.0 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C60 | 26.9125 | 34.8700 | 26.9125 | 34.2000 | 0.0 | 67.0 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C61 | 27.6625 | 45.0050 | 27.6625 | 42.8500 | 0.0 | 215.5 | C70X70C56SD490 | C70X70C56SD490 | C70X70C56SD490 | MISMATCH |
| C64 | 26.9125 | 54.2050 | 26.9125 | 53.5000 | 0.0 | 70.5 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C65 | 26.9125 | 62.9300 | 26.9125 | 62.2250 | 0.0 | 70.5 | C145X100C560SD490 | C145X100C560SD490 | C145X100C560SD490 | MISMATCH |
| C69 | 26.9125 | 76.2050 | 26.9125 | 75.5000 | 0.0 | 70.5 | C120X180C280SD490 | C120X180C280SD490 | C120X180C280SD490 | MISMATCH |
| C75 | 16.2875 | 11.6000 | 16.2875 | 11.6000 | 0.0 | 0.0 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | OK |
| C80 | 16.2875 | 21.1500 | 16.2875 | 23.3000 | 0.0 | 215.0 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C83 | 16.2875 | 34.8700 | 16.2875 | 34.2000 | 0.0 | 67.0 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C85 | 15.4625 | 45.8050 | 15.4625 | 43.6500 | 0.0 | 215.5 | C70X70C56SD490 | C70X70C56SD490 | C70X70C56SD490 | MISMATCH |
| C89 | 15.4625 | 64.6550 | 15.4625 | 63.9500 | 0.0 | 70.5 | C125X120C280SD490 | C125X120C280SD490 | C125X120C280SD490 | MISMATCH |
| C123 | 15.4625 | 76.2050 | 15.4625 | 75.5000 | 0.0 | 70.5 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | MISMATCH |
| C132 | 5.1125 | 11.6000 | 5.1125 | 11.6000 | 0.0 | 0.0 | C70X70C280SD490 | C70X70C280SD490 | C70X70C280SD490 | OK |
| C133 | 5.1125 | 22.8250 | 5.1125 | 24.9750 | 0.0 | 215.0 | C70X70C56SD490 | C70X70C56SD490 | C70X70C56SD490 | MISMATCH |
| C135 | 5.1125 | 34.8700 | 5.1125 | 34.2000 | 0.0 | 67.0 | C70X70C56SD490 | C70X70C56SD490 | C70X70C56SD490 | MISMATCH |
| C151 | 4.6625 | 45.8050 | 4.6625 | 43.6500 | 0.0 | 215.5 | C70X70C56SD490 | C70X70C56SD490 | C70X70C56SD490 | MISMATCH |
| C152 | 4.6625 | 52.7050 | 4.6625 | 52.0000 | 0.0 | 70.5 | C70X70C56SD490 | C70X70C56SD490 | C70X70C56SD490 | MISMATCH |
| C153 | 4.6625 | 64.6550 | 4.6625 | 63.9500 | 0.0 | 70.5 | C70X70C280SD490 | C70X70C280SD490 | C70X70C280SD490 | MISMATCH |
| C154 | -3.3875 | 11.6000 | -3.3875 | 11.6000 | 0.0 | 0.0 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | OK |
| C155 | -3.3875 | 19.6500 | -3.3875 | 21.8000 | 0.0 | 215.0 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C156 | -3.3875 | 33.4700 | -3.3875 | 32.8000 | 0.0 | 67.0 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C157 | -3.3875 | 45.0050 | -3.3875 | 42.8500 | 0.0 | 215.5 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C158 | -3.3875 | 53.0550 | -3.3875 | 52.3500 | 0.0 | 70.5 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C159 | -3.3875 | 64.6550 | -3.3875 | 63.9500 | 0.0 | 70.5 | C70X70C280SD490 | C70X70C280SD490 | C70X70C280SD490 | MISMATCH |
| C160 | -11.2625 | 11.6000 | -12.2125 | 11.6000 | 95.0 | 0.0 | C120X180C280SD490 | C120X180C280SD490 | C120X180C280SD490 | MISMATCH |
| C161 | -11.2625 | 53.0550 | -12.2125 | 52.3500 | 95.0 | 70.5 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C162 | -11.2625 | 64.6550 | -12.2125 | 63.9500 | 95.0 | 70.5 | C70X70C280SD490 | C70X70C280SD490 | C70X70C280SD490 | MISMATCH |
| C164 | -16.8125 | 19.6500 | -16.7625 | 21.8000 | 5.0 | 215.0 | C215X80C560SD490 | C215X80C560SD490 | C215X80C560SD490 | MISMATCH |
| C165 | -16.8125 | 33.4700 | -16.7625 | 32.8000 | 5.0 | 67.0 | C85X230C560SD490 | C85X230C560SD490 | C85X230C560SD490 | MISMATCH |
| C166 | -16.8125 | 45.0050 | -16.7625 | 42.8500 | 5.0 | 215.5 | C120X170C560SD490 | C120X170C560SD490 | C120X170C560SD490 | MISMATCH |
| C167 | -17.8625 | 53.0550 | -18.6125 | 52.3500 | 75.0 | 70.5 | C120X120C56SD490 | C120X120C56SD490 | C120X120C56SD490 | MISMATCH |
| C168 | -17.8625 | 64.6550 | -18.6125 | 63.9500 | 75.0 | 70.5 | C70X70C280SD490 | C70X70C280SD490 | C70X70C280SD490 | MISMATCH |
| C169 | -17.8625 | 11.6000 | -18.6125 | 11.6000 | 75.0 | 0.0 | C120X180C280SD490 | C120X180C280SD490 | C120X180C280SD490 | MISMATCH |
| C170 | -28.3375 | 11.6000 | -28.3375 | 11.6000 | 0.0 | 0.0 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | OK |
| C171 | -28.3375 | 19.6500 | -28.3375 | 21.8000 | 0.0 | 215.0 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | MISMATCH |
| C172 | -28.3375 | 34.8700 | -28.3375 | 34.2000 | 0.0 | 67.0 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | MISMATCH |
| C173 | -28.3375 | 45.0050 | -28.3375 | 42.8500 | 0.0 | 215.5 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | MISMATCH |
| C174 | -28.3375 | 53.0550 | -28.3375 | 52.3500 | 0.0 | 70.5 | C120X120C28SD490 | C120X120C28SD490 | C120X120C28SD490 | MISMATCH |
| C175 | 15.4625 | 53.6500 | 15.4625 | 53.6500 | 0.0 | 0.0 | C125X120C280SD490 | C125X120C280SD490 | C125X120C280SD490 | OK |

## 7. All Column Sections (Rectangular) in Building A

| Section Name | Material | D(cm) | B(cm) |
|-------------|----------|-------|-------|
| C100X100C42 | C420 | 100.0 | 100.0 |
| C100X205C56SD490 | C560SD490 | 100.0 | 205.0 |
| C103X145C56SD490 | C560SD490 | 103.0 | 145.0 |
| C110X205C56SD490 | C560SD490 | 110.0 | 205.0 |
| C113X130C56SD490 | C560SD490 | 113.0 | 130.0 |
| C115X205C56SD490 | C560SD490 | 115.0 | 205.0 |
| C120X120C28SD490 | C280SD490 | 120.0 | 120.0 |
| C120X120C56SD490 | C560SD490 | 120.0 | 120.0 |
| C120X155C56SD490 | C560SD490 | 120.0 | 155.0 |
| C120X160C560SD490 | C560SD490 | 120.0 | 160.0 |
| C120X165C56SD490 | C560SD490 | 120.0 | 165.0 |
| C120X170C560SD490 | C560SD490 | 120.0 | 170.0 |
| C120X175C56SD490 | C560SD490 | 120.0 | 175.0 |
| C120X180C280SD490 | C280SD490 | 120.0 | 180.0 |
| C120X180C56SD490 | C560SD490 | 120.0 | 180.0 |
| C120X185C56SD490 | C560SD490 | 120.0 | 185.0 |
| C120X190C56SD490 | C560SD490 | 120.0 | 190.0 |
| C120X200C56SD490 | C560SD490 | 120.0 | 200.0 |
| C120X205C56SD490 | C560SD490 | 120.0 | 205.0 |
| C120X210C56SD490 | C560SD490 | 120.0 | 210.0 |
| C120X235C56SD490 | C560SD490 | 120.0 | 235.0 |
| C120X250C56SD490 | C560SD490 | 120.0 | 250.0 |
| C125X120C280SD490 | C280SD490 | 125.0 | 120.0 |
| C125X200C56SD49 | C560SD490 | 125.0 | 200.0 |
| C130X130C42 | C420 | 130.0 | 130.0 |
| C130X165C56SD490 | C560SD490 | 130.0 | 165.0 |
| C135X110C560SD490 | C560SD490 | 135.0 | 110.0 |
| C135X145C56SD490 | C560SD490 | 135.0 | 145.0 |
| C135X155C56SD490 | C560SD490 | 135.0 | 155.0 |
| C135X185C56SD490 | C560SD490 | 135.0 | 185.0 |
| C140X105C56SD490 | C560SD490 | 140.0 | 105.0 |
| C140X135C56SD490 | C560SD490 | 140.0 | 135.0 |
| C140X140C28SD490 | C280SD490 | 140.0 | 140.0 |
| C140X140C56SD490 | C560SD490 | 140.0 | 140.0 |
| C140X155C56SD490 | C560SD490 | 140.0 | 155.0 |
| C140X165C56SD490 | C560SD490 | 140.0 | 165.0 |
| C145X100C560SD490 | C560SD490 | 145.0 | 100.0 |
| C145X165C56SD490 | C560SD490 | 145.0 | 165.0 |
| C150X150C42 | C420 | 150.0 | 150.0 |
| C150X165C56SD490 | C560SD490 | 150.0 | 165.0 |
| C150X170C56SD490 | C560SD490 | 150.0 | 170.0 |
| C155X140C56SD490 | C560SD490 | 155.0 | 140.0 |
| C165X120C56SD490 | C560SD490 | 165.0 | 120.0 |
| C165X145C56SD490 | C560SD490 | 165.0 | 145.0 |
| C165X170C56SD490 | C560SD490 | 165.0 | 170.0 |
| C167X120C56SD490 | C560SD490 | 167.0 | 120.0 |
| C180X100C56SD490 | C560SD490 | 180.0 | 100.0 |
| C180X140C56SD490 | C560SD490 | 180.0 | 140.0 |
| C180X80C56SD490 | C560SD490 | 180.0 | 80.0 |
| C185X120C56SD490 | C560SD490 | 185.0 | 120.0 |
| C190X120C56SD490 | C560SD490 | 190.0 | 120.0 |
| C190X130C56SD490 | C560SD490 | 190.0 | 130.0 |
| C195X115C56SD490 | C560SD490 | 195.0 | 115.0 |
| C205X135C56SD490 | C560SD490 | 205.0 | 135.0 |
| C205X85C56SD490 | C560SD490 | 205.0 | 85.0 |
| C215X110C56SD490 | C560SD490 | 215.0 | 110.0 |
| C215X80C560SD490 | C560SD490 | 215.0 | 80.0 |
| C230X105C56SD490 | C560SD490 | 230.0 | 105.0 |
| C230X120C56SD490 | C560SD490 | 230.0 | 120.0 |
| C60X60C28 | C280SD490 | 60.0 | 60.0 |
| C70X70C280SD490 | C280SD490 | 70.0 | 70.0 |
| C70X70C49 | STEEL | 70.0 | 70.0 |
| C70X70C56SD490 | C560SD490 | 70.0 | 70.0 |
| C70X70C630 | C630 | 70.0 | 70.0 |
| C75X195C56SD490 | C560SD490 | 75.0 | 195.0 |
| C77X190C56SD490 | C560SD490 | 77.0 | 190.0 |
| C80X80C28 | C280 | 80.0 | 80.0 |
| C83X175C56SD490 | C560SD490 | 83.0 | 175.0 |
| C85X230C560SD490 | C560SD490 | 85.0 | 230.0 |

## 8. All Column Sections (Rectangular) in Building D

| Section Name | Material | D(cm) | B(cm) |
|-------------|----------|-------|-------|
| C100X100C420SD490 | C420SD490 | 100.0 | 100.0 |
| C100X205C56SD490 | C560SD490 | 100.0 | 205.0 |
| C103X145C56SD490 | C560SD490 | 103.0 | 145.0 |
| C110X205C56SD490 | C560SD490 | 110.0 | 205.0 |
| C113X130C56SD490 | C560SD490 | 113.0 | 130.0 |
| C115X205C56SD490 | C560SD490 | 115.0 | 205.0 |
| C120X120C28SD490 | C280SD490 | 120.0 | 120.0 |
| C120X120C56SD490 | C560SD490 | 120.0 | 120.0 |
| C120X155C56SD490 | C560SD490 | 120.0 | 155.0 |
| C120X160C560SD490 | C560SD490 | 120.0 | 160.0 |
| C120X165C56SD490 | C560SD490 | 120.0 | 165.0 |
| C120X170C560SD490 | C560SD490 | 120.0 | 170.0 |
| C120X175C56SD490 | C560SD490 | 120.0 | 175.0 |
| C120X180C280SD490 | C280SD490 | 120.0 | 180.0 |
| C120X180C56SD490 | C560SD490 | 120.0 | 180.0 |
| C120X185C56SD490 | C560SD490 | 120.0 | 185.0 |
| C120X190C56SD490 | C560SD490 | 120.0 | 190.0 |
| C120X200C56SD490 | C560SD490 | 120.0 | 200.0 |
| C120X205C56SD490 | C560SD490 | 120.0 | 205.0 |
| C120X210C56SD490 | C560SD490 | 120.0 | 210.0 |
| C120X235C56SD490 | C560SD490 | 120.0 | 235.0 |
| C120X250C56SD490 | C560SD490 | 120.0 | 250.0 |
| C125X120C280SD490 | C280SD490 | 125.0 | 120.0 |
| C125X200C56SD49 | C560SD490 | 125.0 | 200.0 |
| C130X130C420SD490 | C420SD490 | 130.0 | 130.0 |
| C130X165C56SD490 | C560SD490 | 130.0 | 165.0 |
| C135X110C560SD490 | C560SD490 | 135.0 | 110.0 |
| C135X145C56SD490 | C560SD490 | 135.0 | 145.0 |
| C135X155C56SD490 | C560SD490 | 135.0 | 155.0 |
| C135X185C56SD490 | C560SD490 | 135.0 | 185.0 |
| C140X105C56SD490 | C560SD490 | 140.0 | 105.0 |
| C140X135C56SD490 | C560SD490 | 140.0 | 135.0 |
| C140X140C28SD490 | C280SD490 | 140.0 | 140.0 |
| C140X140C56SD490 | C560SD490 | 140.0 | 140.0 |
| C140X155C56SD490 | C560SD490 | 140.0 | 155.0 |
| C140X165C56SD490 | C560SD490 | 140.0 | 165.0 |
| C145X100C560SD490 | C560SD490 | 145.0 | 100.0 |
| C145X165C56SD490 | C560SD490 | 145.0 | 165.0 |
| C150X150C420SD490 | C420SD490 | 150.0 | 150.0 |
| C150X165C56SD490 | C560SD490 | 150.0 | 165.0 |
| C150X170C56SD490 | C560SD490 | 150.0 | 170.0 |
| C155X140C56SD490 | C560SD490 | 155.0 | 140.0 |
| C165X120C56SD490 | C560SD490 | 165.0 | 120.0 |
| C165X145C56SD490 | C560SD490 | 165.0 | 145.0 |
| C165X170C56SD490 | C560SD490 | 165.0 | 170.0 |
| C167X120C56SD490 | C560SD490 | 167.0 | 120.0 |
| C180X100C56SD490 | C560SD490 | 180.0 | 100.0 |
| C180X140C56SD490 | C560SD490 | 180.0 | 140.0 |
| C180X80C56SD490 | C560SD490 | 180.0 | 80.0 |
| C185X120C56SD490 | C560SD490 | 185.0 | 120.0 |
| C190X120C56SD490 | C560SD490 | 190.0 | 120.0 |
| C190X130C56SD490 | C560SD490 | 190.0 | 130.0 |
| C195X115C56SD490 | C560SD490 | 195.0 | 115.0 |
| C205X135C56SD490 | C560SD490 | 205.0 | 135.0 |
| C205X85C56SD490 | C560SD490 | 205.0 | 85.0 |
| C215X110C56SD490 | C560SD490 | 215.0 | 110.0 |
| C215X80C560SD490 | C560SD490 | 215.0 | 80.0 |
| C230X105C56SD490 | C560SD490 | 230.0 | 105.0 |
| C230X120C56SD490 | C560SD490 | 230.0 | 120.0 |
| C60X60C28 | C280SD490 | 60.0 | 60.0 |
| C70X70C280SD490 | C280SD490 | 70.0 | 70.0 |
| C70X70C49 | STEEL | 70.0 | 70.0 |
| C70X70C56SD490 | C560SD490 | 70.0 | 70.0 |
| C70X70C630 | C630 | 70.0 | 70.0 |
| C75X195C56SD490 | C560SD490 | 75.0 | 195.0 |
| C77X190C56SD490 | C560SD490 | 77.0 | 190.0 |
| C80X80C28 | C280 | 80.0 | 80.0 |
| C83X175C56SD490 | C560SD490 | 83.0 | 175.0 |
| C85X230C560SD490 | C560SD490 | 85.0 | 230.0 |

## 9. SRC Sections

### Building A SRC Sections

| Section Name | Material | Shape | D(cm) | B(cm) |
|-------------|----------|-------|-------|-------|
| SRB75X90C28 | C280SD490 | Rectangular | 90.0 | 75.0 |
| SRB75X90C35 | C350SD490 | Rectangular | 90.0 | 75.0 |
| SRB75X90C42SD490 | C420SD490 | Rectangular | 90.0 | 75.0 |
| SRB75X90C49SD490 | STEEL | Rectangular | 90.0 | 75.0 |
| SRB75X90C56SD490 | C560SD490 | Rectangular | 90.0 | 75.0 |
| SRB80X120C56SD490 | C560SD490 | Rectangular | 120.0 | 80.0 |
| SRB80X90C28 | C280SD490 | Rectangular | 90.0 | 80.0 |
| SRB80X90C35 | C350SD490 | Rectangular | 90.0 | 80.0 |
| SRB80X90C42SD490 | C420SD490 | Rectangular | 90.0 | 80.0 |
| SRB80X90C49SD490 | STEEL | Rectangular | 90.0 | 80.0 |
| SRB80X90C56SD490 | C560SD490 | Rectangular | 90.0 | 80.0 |
| SRB85X90C35 | C350SD490 | Rectangular | 90.0 | 85.0 |
| SRB85X90C42SD490 | C420SD490 | Rectangular | 90.0 | 85.0 |
| SRB85X90C49SD490 | STEEL | Rectangular | 90.0 | 85.0 |
| SRB85X90C56SD490 | C560SD490 | Rectangular | 90.0 | 85.0 |
| SRC100X100C28 | C280SD490 | Rectangular | 100.0 | 100.0 |
| SRC100X100C35 | C350SD490 | Rectangular | 100.0 | 100.0 |
| SRC100X100C42SD490 | C420SD490 | Rectangular | 100.0 | 100.0 |
| SRC103CX145C56SD490 | C560SD490 | Rectangular | 103.0 | 145.0 |
| SRC105X120C28 | C280SD490 | Rectangular | 105.0 | 120.0 |
| SRC105X120C35 | C350SD490 | Rectangular | 105.0 | 120.0 |
| SRC105X120C42SD490 | C420SD490 | Rectangular | 105.0 | 120.0 |
| SRC105X120C49SD490 | STEEL | Rectangular | 105.0 | 120.0 |
| SRC105X120C56SD490 | C560SD490 | Rectangular | 105.0 | 120.0 |
| SRC113X130C56SD490 | C560SD490 | Rectangular | 113.0 | 130.0 |
| SRC120X100C42SD490 | C420SD490 | Rectangular | 120.0 | 100.0 |
| SRC120X100C49SD490 | STEEL | Rectangular | 120.0 | 100.0 |
| SRC120X120C28 | C280SD490 | Rectangular | 120.0 | 120.0 |
| SRC120X120C28SD490 | C280SD490 | Rectangular | 120.0 | 120.0 |
| SRC120X120C35 | C350SD490 | Rectangular | 120.0 | 120.0 |
| SRC120X120C42SD490 | C420SD490 | Rectangular | 120.0 | 120.0 |
| SRC120X120C49SD490 | STEEL | Rectangular | 120.0 | 120.0 |
| SRC120X120C56SD490 | C560SD490 | Rectangular | 120.0 | 120.0 |
| SRC120X145C28SD490 | C280SD490 | Rectangular | 120.0 | 145.0 |
| SRC120X145C56SD490 | C560SD490 | Rectangular | 120.0 | 145.0 |
| SRC120X170C56SD490 | C560SD490 | Rectangular | 120.0 | 170.0 |
| SRC120X175C56SD490 | C560SD490 | Rectangular | 120.0 | 175.0 |
| SRC120X178C56SD490 | C560SD490 | Rectangular | 120.0 | 178.0 |
| SRC120X190C56SD490 | C560SD490 | Rectangular | 120.0 | 190.0 |
| SRC120X195C56SD490 | C560SD490 | Rectangular | 120.0 | 195.0 |
| SRC132X120C56SD490 | C560SD490 | Rectangular | 132.0 | 120.0 |
| SRC133X120C56SD490 | C560SD490 | Rectangular | 133.0 | 120.0 |
| SRC140X120C28SD490 | C280SD490 | Rectangular | 140.0 | 120.0 |
| SRC140X120C42SD490 | C420SD490 | Rectangular | 140.0 | 120.0 |
| SRC140X120C49SD490 | STEEL | Rectangular | 140.0 | 120.0 |
| SRC140X140C49SD490 | STEEL | Rectangular | 140.0 | 140.0 |
| SRC140X140C56SD490 | C560SD490 | Rectangular | 140.0 | 140.0 |
| SRC145X145C56SD490 | C560SD490 | Rectangular | 145.0 | 145.0 |
| SRC155X120C28SD490 | C280SD490 | Rectangular | 155.0 | 120.0 |
| SRC157X120C56SD490 | C560SD490 | Rectangular | 157.0 | 120.0 |
| SRC162X120C56SD490 | C560SD490 | Rectangular | 162.0 | 120.0 |
| SRC167X120C56SD490 | C560SD490 | Rectangular | 167.0 | 120.0 |
| SRC172X120C56SD490 | C560SD490 | Rectangular | 172.0 | 120.0 |
| SRC173X120C56SD490 | C560SD490 | Rectangular | 173.0 | 120.0 |
| SRC180X80C28 | C280SD490 | Rectangular | 180.0 | 80.0 |
| SRC180X80C35 | C350SD490 | Rectangular | 180.0 | 80.0 |
| SRC180X80C42SD490 | C420SD490 | Rectangular | 180.0 | 80.0 |
| SRC180X80C49SD490 | STEEL | Rectangular | 180.0 | 80.0 |
| SRC180X80C56SD490 | C560SD490 | Rectangular | 180.0 | 80.0 |
| SRC180X90C49SD490 | STEEL | Rectangular | 180.0 | 90.0 |
| SRC180X90C56SD490 | C560SD490 | Rectangular | 180.0 | 90.0 |
| SRC190X80C56SD490 | C560SD490 | Rectangular | 190.0 | 80.0 |
| SRC192X120C56SD490 | C560SD490 | Rectangular | 192.0 | 120.0 |
| SRC197X80C28 | C280SD490 | Rectangular | 197.0 | 80.0 |
| SRC197X80C35 | C350SD490 | Rectangular | 197.0 | 80.0 |
| SRC197X80C42SD490 | C420SD490 | Rectangular | 197.0 | 80.0 |
| SRC197X80C49SD490 | STEEL | Rectangular | 197.0 | 80.0 |
| SRC197X80C56SD490 | C560SD490 | Rectangular | 197.0 | 80.0 |
| SRC197X90C49SD490 | STEEL | Rectangular | 197.0 | 90.0 |
| SRC197X90C56SD490 | C560SD490 | Rectangular | 197.0 | 90.0 |
| SRC75X195C56SD490 | C560SD490 | Rectangular | 75.0 | 195.0 |
| SRC77X190C56SD490 | C560SD490 | Rectangular | 77.0 | 190.0 |
| SRC83X175C56SD490 | C560SD490 | Rectangular | 83.0 | 175.0 |

### Building D SRC Sections

| Section Name | Material | Shape | D(cm) | B(cm) |
|-------------|----------|-------|-------|-------|
| SRB75X90C28 | C280SD490 | Rectangular | 90.0 | 75.0 |
| SRB75X90C35 | C350SD490 | Rectangular | 90.0 | 75.0 |
| SRB75X90C42SD490 | C420SD490 | Rectangular | 90.0 | 75.0 |
| SRB75X90C49SD490 | STEEL | Rectangular | 90.0 | 75.0 |
| SRB75X90C56SD490 | C560SD490 | Rectangular | 90.0 | 75.0 |
| SRB80X120C56SD490 | C560SD490 | Rectangular | 120.0 | 80.0 |
| SRB80X90C28 | C280SD490 | Rectangular | 90.0 | 80.0 |
| SRB80X90C35 | C350SD490 | Rectangular | 90.0 | 80.0 |
| SRB80X90C42SD490 | C420SD490 | Rectangular | 90.0 | 80.0 |
| SRB80X90C49SD490 | STEEL | Rectangular | 90.0 | 80.0 |
| SRB80X90C56SD490 | C560SD490 | Rectangular | 90.0 | 80.0 |
| SRB85X90C35 | C350SD490 | Rectangular | 90.0 | 85.0 |
| SRB85X90C42SD490 | C420SD490 | Rectangular | 90.0 | 85.0 |
| SRB85X90C49SD490 | STEEL | Rectangular | 90.0 | 85.0 |
| SRB85X90C56SD490 | C560SD490 | Rectangular | 90.0 | 85.0 |
| SRC100X100C28 | C280SD490 | Rectangular | 100.0 | 100.0 |
| SRC100X100C35 | C350SD490 | Rectangular | 100.0 | 100.0 |
| SRC100X100C42SD490 | C420SD490 | Rectangular | 100.0 | 100.0 |
| SRC103CX145C56SD490 | C560SD490 | Rectangular | 103.0 | 145.0 |
| SRC105X120C28 | C280SD490 | Rectangular | 105.0 | 120.0 |
| SRC105X120C35 | C350SD490 | Rectangular | 105.0 | 120.0 |
| SRC105X120C42SD490 | C420SD490 | Rectangular | 105.0 | 120.0 |
| SRC105X120C49SD490 | STEEL | Rectangular | 105.0 | 120.0 |
| SRC105X120C56SD490 | C560SD490 | Rectangular | 105.0 | 120.0 |
| SRC113X130C56SD490 | C560SD490 | Rectangular | 113.0 | 130.0 |
| SRC120X100C42SD490 | C420SD490 | Rectangular | 120.0 | 100.0 |
| SRC120X100C49SD490 | STEEL | Rectangular | 120.0 | 100.0 |
| SRC120X120C28 | C280SD490 | Rectangular | 120.0 | 120.0 |
| SRC120X120C28SD490 | C280SD490 | Rectangular | 120.0 | 120.0 |
| SRC120X120C35 | C350SD490 | Rectangular | 120.0 | 120.0 |
| SRC120X120C42SD490 | C420SD490 | Rectangular | 120.0 | 120.0 |
| SRC120X120C49SD490 | STEEL | Rectangular | 120.0 | 120.0 |
| SRC120X120C56SD490 | C560SD490 | Rectangular | 120.0 | 120.0 |
| SRC120X145C28SD490 | C280SD490 | Rectangular | 120.0 | 145.0 |
| SRC120X145C56SD490 | C560SD490 | Rectangular | 120.0 | 145.0 |
| SRC120X170C56SD490 | C560SD490 | Rectangular | 120.0 | 170.0 |
| SRC120X175C56SD490 | C560SD490 | Rectangular | 120.0 | 175.0 |
| SRC120X178C56SD490 | C560SD490 | Rectangular | 120.0 | 178.0 |
| SRC120X190C56SD490 | C560SD490 | Rectangular | 120.0 | 190.0 |
| SRC120X195C56SD490 | C560SD490 | Rectangular | 120.0 | 195.0 |
| SRC132X120C56SD490 | C560SD490 | Rectangular | 132.0 | 120.0 |
| SRC133X120C56SD490 | C560SD490 | Rectangular | 133.0 | 120.0 |
| SRC140X120C28SD490 | C280SD490 | Rectangular | 140.0 | 120.0 |
| SRC140X120C42SD490 | C420SD490 | Rectangular | 140.0 | 120.0 |
| SRC140X120C49SD490 | STEEL | Rectangular | 140.0 | 120.0 |
| SRC140X140C49SD490 | STEEL | Rectangular | 140.0 | 140.0 |
| SRC140X140C56SD490 | C560SD490 | Rectangular | 140.0 | 140.0 |
| SRC145X145C56SD490 | C560SD490 | Rectangular | 145.0 | 145.0 |
| SRC155X120C28SD490 | C280SD490 | Rectangular | 155.0 | 120.0 |
| SRC157X120C56SD490 | C560SD490 | Rectangular | 157.0 | 120.0 |
| SRC162X120C56SD490 | C560SD490 | Rectangular | 162.0 | 120.0 |
| SRC167X120C56SD490 | C560SD490 | Rectangular | 167.0 | 120.0 |
| SRC172X120C56SD490 | C560SD490 | Rectangular | 172.0 | 120.0 |
| SRC173X120C56SD490 | C560SD490 | Rectangular | 173.0 | 120.0 |
| SRC180X80C28 | C280SD490 | Rectangular | 180.0 | 80.0 |
| SRC180X80C35 | C350SD490 | Rectangular | 180.0 | 80.0 |
| SRC180X80C42SD490 | C420SD490 | Rectangular | 180.0 | 80.0 |
| SRC180X80C49SD490 | STEEL | Rectangular | 180.0 | 80.0 |
| SRC180X80C56SD490 | C560SD490 | Rectangular | 180.0 | 80.0 |
| SRC180X90C49SD490 | STEEL | Rectangular | 180.0 | 90.0 |
| SRC180X90C56SD490 | C560SD490 | Rectangular | 180.0 | 90.0 |
| SRC190X80C56SD490 | C560SD490 | Rectangular | 190.0 | 80.0 |
| SRC192X120C56SD490 | C560SD490 | Rectangular | 192.0 | 120.0 |
| SRC197X80C28 | C280SD490 | Rectangular | 197.0 | 80.0 |
| SRC197X80C35 | C350SD490 | Rectangular | 197.0 | 80.0 |
| SRC197X80C42SD490 | C420SD490 | Rectangular | 197.0 | 80.0 |
| SRC197X80C49SD490 | STEEL | Rectangular | 197.0 | 80.0 |
| SRC197X80C56SD490 | C560SD490 | Rectangular | 197.0 | 80.0 |
| SRC197X90C49SD490 | STEEL | Rectangular | 197.0 | 90.0 |
| SRC197X90C56SD490 | C560SD490 | Rectangular | 197.0 | 90.0 |
| SRC75X195C56SD490 | C560SD490 | Rectangular | 75.0 | 195.0 |
| SRC77X190C56SD490 | C560SD490 | Rectangular | 77.0 | 190.0 |
| SRC83X175C56SD490 | C560SD490 | Rectangular | 83.0 | 175.0 |

## 10. Key Findings Summary

### Grid Differences

- A vs OLD: 22 grid differences

- D vs OLD: 4 grid differences

- A vs D: 24 grid differences

### Section Dimension Issues

- No section name/dimension mismatches found in any model.

### Column Connectivity

- A vs OLD coordinate mismatches: 54

- D vs OLD coordinate mismatches: 16

- A columns missing from OLD basement: 2

- D columns missing from OLD basement: 0


**CRITICAL:** Some above-ground columns in A/D have no corresponding basement column in OLD. 
These columns will be disconnected in the merged model.
