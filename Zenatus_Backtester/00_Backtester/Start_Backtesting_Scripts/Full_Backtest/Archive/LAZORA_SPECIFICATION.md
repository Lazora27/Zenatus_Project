# LAZORA-VERFAHREN - COMPLETE SPECIFICATION

## MATHEMATISCHE GRUNDLAGE

### PHASE 1: INITIAL SAMPLING (500 Kombinationen)
**Method: Sobol Sequence**
- Quasi-Random Low-Discrepancy Sequence
- Garantiert gleichmäßige Raum-Abdeckung
- Reproduzierbar (Seed=42)

**Formel:**
```
Sobol Points = {x₁, x₂, ..., x₅₀₀} ∈ [0,1]ᴰ
wo D = Anzahl Parameter (2D-10D)
```

**Mapping zu echten Parameter-Werten:**
```
Für jeden Parameter p:
real_value = start + sobol_point * (end - start)

Beispiel Period [10, 60]:
sobol_point = 0.25
real_value = 10 + 0.25 * (60 - 10) = 22.5 → 23 (gerundet wenn int)
```

---

### PHASE 2: ADAPTIVE REFINEMENT (500 Kombinationen)
**Method: Density-Based Sampling in Hot Zones**

**Algorithmus:**
1. Analyse Phase 1 Ergebnisse
2. Identifiziere "Hot Zones" (Top 20% Sharpe Ratio)
3. Berechne Density Kernel um Hot Zones
4. Sample neue 500 Points mit höherer Dichte in Hot Zones

**Formel:**
```
Kernel Density Estimation (KDE):
f(x) = (1/n) Σ K((x - xᵢ)/h)

wo:
- K = Gaussian Kernel
- h = Bandwidth (adaptiv)
- xᵢ = Hot Zone Centers
```

**Sampling Strategy:**
```
80% of samples → Inner 50% of Hot Zones (dicht)
20% of samples → Outer 50% of Hot Zones (explorativ)
```

---

### PHASE 3: ULTRA-FINE TUNING (1500 Kombinationen)
**Method: Micro-Grid around Best Points**

**Algorithmus:**
1. Identifiziere Top 5 Kandidaten aus Phase 2
2. Für jeden Kandidaten: Erstelle 300-Sample Micro-Grid
3. Grid-Size: ±5% um Kandidat

**Formel:**
```
Für jeden Parameter p des Kandidaten c:
micro_range = [c.p * 0.95, c.p * 1.05]
micro_steps = linspace(micro_range, 60)  # 60 steps pro Parameter
```

---

## HEATMAP GENERATION

### 2D-4D: Standard Visualization
**2D:** Scatter Plot mit Farbkodierung
**3D:** 3D Scatter mit Farbkodierung
**4D:** Multiple 3D Projections + Interactive

### 5D-10D: Dimensionality Reduction
**Method: t-SNE oder UMAP**
```python
from sklearn.manifold import TSNE

tsne = TSNE(n_components=3, perplexity=30, n_iter=1000)
coords_3d = tsne.fit_transform(parameter_combinations)
```

**Visualization:**
- 3D Scatter Plot
- Farbe = Sharpe Ratio
- Größe = Return / DD Ratio

---

## COLOR SCHEME

**Grün-Rot Gradient:**
```python
Sharpe Ratio Mapping:
SR < 0.0  → Dark Red (#8B0000)
SR = 0.0  → Red (#FF0000)
SR = 1.0  → Yellow (#FFFF00)
SR = 2.0  → Light Green (#90EE90)
SR > 3.0  → Dark Green (#006400)
```

---

## EFFICIENCY ANALYSIS

**Beispiel: 4D Parameter Space (1M Kombinationen)**

| Phase | Samples | Coverage | Time | Cumulative |
|-------|---------|----------|------|------------|
| 1     | 500     | ~5%      | 2h   | 500        |
| 2     | 500     | +10%     | 2h   | 1000       |
| 3     | 1500    | +15%     | 6h   | 2500       |
| **Total** | **2500** | **30%** | **10h** | **2500** |

**vs. Exhaustive:** 1M Kombinationen × 2s = 2,000,000s = 23 Tage!

**Speedup: 55x**

---

## IMPLEMENTATION STRATEGY

### Step 1: Generate Sobol Samples (DONE)
```python
from scipy.stats import qmc
sobol = qmc.Sobol(d=n_params, scramble=True, seed=42)
samples = sobol.random(500)
```

### Step 2: Map to Real Parameters
```python
real_params = []
for sample in samples:
    params = {}
    for i, (name, config) in enumerate(param_config.items()):
        value = config['start'] + sample[i] * (config['end'] - config['start'])
        if config['type'] == 'int':
            value = int(round(value))
        params[name] = value
    real_params.append(params)
```

### Step 3: Run Backtest on all 500 Samples
```python
results = []
for params in real_params:
    result = backtest_indicator(params)
    results.append(result)
```

### Step 4: Generate Heatmap
```python
if n_dims <= 3:
    plot_standard_heatmap(results)
else:
    plot_tsne_heatmap(results)
```

### Step 5: Identify Hot Zones
```python
top_20_percent = sorted(results, key=lambda x: x['sharpe'], reverse=True)[:100]
hot_zones = cluster_points(top_20_percent)
```

---

## NEXT STEPS

1. ✅ Implement Sobol Sampling in Backtest Script
2. ✅ Run Phase 1 on all 595 Indicators
3. ✅ Generate Heatmaps
4. ⏳ Analyze Hot Zones
5. ⏳ Implement Phase 2
6. ⏳ Implement Phase 3

---

## BENEFITS

✅ **Efficiency:** 2,500 tests statt 1,000,000
✅ **Intelligence:** Adaptiv + Lernend
✅ **Visualization:** Heatmaps für Insights
✅ **Reproducibility:** Seed-basiert
✅ **Scalability:** Funktioniert für 2D-10D
✅ **Quality:** Findet echte Optima, nicht nur Random Good Points

---

**BEREIT FÜR IMPLEMENTATION?**
