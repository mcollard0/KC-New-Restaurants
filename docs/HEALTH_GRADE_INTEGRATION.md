# Health Inspection Grade Integration

## Overview
The AI prediction system now integrates health inspection data to adjust the "Will I Like This Restaurant" rating. Poor health scores reduce the predicted enjoyment rating, with recent violations weighted more heavily.

## How It Works

### Health Grade Penalties
Health grades are mapped to rating penalties:

| Health Grade | Base Penalty | Effect |
|--------------|--------------|---------|
| A+, A, A-    | 0.0★         | No penalty - good health practices |
| B+           | 0.0★         | Minimal concern |
| B, B-        | 0.1★         | Minor penalty |
| C+           | 0.2★         | Small penalty |
| C, C-        | 0.5★         | Moderate penalty |
| D, D+, D-    | 1.0★         | Major penalty |
| F, G, H+     | 1.5★         | Severe penalty |

### Additional Penalties
**Critical Violations**: Extra penalties for high average critical violations:
- 2+ critical violations avg: +0.3★ penalty
- 1+ critical violations avg: +0.15★ penalty

### Recency Weighting
Recent inspections have more impact than old ones:

| Inspection Age | Weight | Effect |
|----------------|--------|---------|
| < 6 months     | 100%   | Full penalty applied |
| 6-12 months    | 80%    | Slight decay |
| 1-2 years      | 50%    | Half penalty |
| > 2 years      | 30%    | Minimal impact |

## Example Scenarios

### Scenario 1: Recent F Grade
- **Base Rating**: 4.8★ (A+)
- **Health Grade**: F (3 critical violations avg, 30 days old)
- **Penalty**: 1.5 (F grade) + 0.3 (critical) × 1.0 (recent) = 1.8★
- **Final Rating**: 3.0★ (D)
- **Impact**: Restaurant drops from A+ to D due to serious recent health violations

### Scenario 2: Old D Grade
- **Base Rating**: 4.2★ (B+)
- **Health Grade**: D (1.5 critical violations avg, 800 days old)
- **Penalty**: 1.0 (D grade) + 0.15 (critical) × 0.3 (old) = 0.34★
- **Final Rating**: 3.86★ (C+)
- **Impact**: Minor reduction since violations are old

### Scenario 3: Recent C Grade
- **Base Rating**: 3.7★ (C+)
- **Health Grade**: C (0.5 critical violations avg, 100 days old)
- **Penalty**: 0.5 (C grade) × 0.8 (somewhat recent) = 0.4★
- **Final Rating**: 3.3★ (C)
- **Impact**: Moderate reduction for average health practices

### Scenario 4: Good A Grade
- **Base Rating**: 4.5★ (A)
- **Health Grade**: A (0 critical violations, 60 days old)
- **Penalty**: 0.0★
- **Final Rating**: 4.5★ (A)
- **Impact**: No change - restaurant maintains high rating

## Why This Matters

Health inspection scores reflect:
- **Food safety practices**: Critical violations can indicate unsafe food handling
- **Cleanliness**: Reflects restaurant hygiene standards
- **Management quality**: Shows attention to detail and regulations
- **Your safety**: Protects you from potential foodborne illness

By integrating health scores into AI predictions, the system ensures your "enjoyment" rating accounts for an important factor: whether you'll feel confident about the restaurant's food safety practices.

## Data Sources

Health inspection data is fetched from:
- **Kansas City MO**: inspectionsonline.us/mo/usakansascity
- **Kansas City KS**: inspectionsonline.us/ks/wyandotte  
- **Johnson County KS**: inspectionsonline.us/ks/joco (Overland Park, Olathe, etc.)
- **Other KC Metro**: Independence, Lee's Summit, Blue Springs

The system automatically detects the correct jurisdiction based on the restaurant's address and prioritizes jurisdictions by restaurant density.
