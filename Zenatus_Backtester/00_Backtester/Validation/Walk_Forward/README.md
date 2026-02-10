# WALK-FORWARD ANALYSIS - OVERVIEW

## KATEGORIE: OUT-OF-SAMPLE VALIDATION METHODS

Walk-Forward Analysis gehört zur Kategorie **"Out-of-Sample Testing"** oder **"Time-Series Cross-Validation"**.

### VERWANDTE METHODEN:

1. **Walk-Forward Analysis** (implementiert)
   - Rolling Window
   - Anchored Walk-Forward
   - Combinatorial Walk-Forward

2. **K-Fold Cross-Validation** (Time-Series aware)
   - Blocked Cross-Validation
   - Purged K-Fold
   - Embargo

3. **Monte Carlo Validation**
   - Bootstrap Resampling
   - Permutation Tests
   - Synthetic Data Generation

4. **Kelly Criterion**
   - Optimal Position Sizing
   - Fractional Kelly
   - Risk-Adjusted Sizing

---

## CURRENT IMPLEMENTATION:

### Walk-Forward 80/20 (IMPLEMENTED)
```
Training: 01.01.2023 - 20.09.2025 (80%)
Testing:  20.09.2025 - 01.01.2026 (20%)
```

**Output:**
- Train_Return, Train_DD, Train_Sharpe, etc.
- Test_Return, Test_DD, Test_Sharpe, etc.
- Full_Return, Full_DD, Full_Sharpe, etc.

---

## FOLDER STRUCTURE:

```
09_Validation_Methods/
├── Walk_Forward/          (Current implementation)
│   ├── 80_20_Split/
│   ├── Rolling_Window/    (TODO)
│   └── Anchored/          (TODO)
├── Kelly_Criterion/       (TODO)
│   ├── Full_Kelly/
│   └── Fractional_Kelly/
├── Monte_Carlo/           (TODO)
│   ├── Bootstrap/
│   └── Permutation/
└── Cross_Validation/      (TODO)
    ├── Blocked/
    └── Purged_KFold/
```

---

## NEXT STEPS:

1. Move Walk-Forward scripts to 09_Validation_Methods/Walk_Forward/
2. Implement Rolling Window Walk-Forward
3. Implement Kelly Criterion
4. Implement Monte Carlo Validation

---

**Current Focus: Lazora Phase 1 with Walk-Forward 80/20**
