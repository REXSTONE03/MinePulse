# MinePulse AI — Core Project Assumptions

> [!IMPORTANT]
> **Synthetic Dataset Disclaimer**
> This dataset is synthetic and is intended for methodological evaluation and prototype validation, not as evidence of real mining-site performance.

This document lists the assumptions, boundary parameters, and anti-leakage rules governing the MinePulse AI predictive models and simulation engine.

---

## 1. Information Boundaries & Anti-Leakage Constraints

To prevent temporal and data leakage, all data pipelines and training scripts must enforce strict information boundaries. For any evaluation or training run at a specific timestamp, we define:

* **Prediction Timestamp ($t_{pred}$)**: The exact logical clock date/time at which the prediction is made.
* **Information Available at Prediction ($\mathcal{I}_{t_{pred}}$)**: Database records dated strictly $\le t_{pred}$.
  * Includes operating hours accumulated up to $t_{pred}$, completed maintenance plans $\le t_{pred}$, failures logged $\le t_{pred}$, and inventory balances at $t_{pred}$.
  * Excludes future operating hours, future failures, future part usage, and future deliveries.
* **Forecast Horizon ($H$)**: The forward window $[t_{pred}, t_{pred} + 14 \text{ days}]$ for which failure risks and demand are predicted.
* **Future Ground Truth ($\mathcal{G}_{future}$)**: Unobserved database records dated $> t_{pred}$. This dataset is strictly hidden from the feature generator and model inference during testing.

### Historical Snapshot Generation
To train and test models historically without leakage:
1. The training pipeline selects a past timestamp $t_{split}$.
2. A database view is generated that filters out all transactions, usage logs, failures, and updates where `timestamp > t_split`.
3. Running hours for components are rolled back to their values as of $t_{split}$.
4. Features are constructed solely from this rolled-back snapshot.

---

## 2. Modeling & Causal Wear Assumptions

1. **Component Wear Resets**: We assume that replacing a component resets its cumulative operating hours to zero.
2. **Weibull Wear Process**: We assume component degradation follows a non-stationary Weibull process where the probability of failure increases with component age.
3. **No Cascading Failures**: For the initial model, failures of different components on the same vehicle are assumed stochastically independent.
4. **Maintenance Delay Penalties**: Delaying scheduled maintenance beyond its target hours accelerates the wear rate exponentially.

---

## 3. Financial & Cost Assumptions

Since exact mining financial figures vary, MinePulse AI uses a normalized relative cost model:

* **Unit Cost coefficient ($C_{hold}$)**: 0.05% of the part's unit cost per day (equivalent to ~18% annual carrying cost).
* **Downtime penalty coefficient ($C_{down}$)**: Expressed as a multiplier relative to the average part unit cost. We assume:
  * For critical vehicle parts (e.g. engine, transmission): $C_{down} = 100 \times C_{hold}$ per hour of downtime.
  * For minor wear items: $C_{down} = 10 \times C_{hold}$ per hour.
* This relative formulation avoids arbitrary dollar claims while preserving the mathematical balance required to optimize the inventory objective function.
