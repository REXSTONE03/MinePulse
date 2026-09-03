# MinePulse AI — Mathematical & Predictive Methodology

> [!IMPORTANT]
> **Synthetic Dataset Disclaimer**
> This dataset is synthetic and is intended for methodological evaluation and prototype validation, not as evidence of real mining-site performance.

This document details the machine learning prediction tasks, demand forecasting structure, uncertainty quantification, and decision-support optimization model.

---

## 1. Explicit Machine Learning & Prediction Tasks

To support operational decisions, the system partitions predictive inference into three distinct mathematical tasks:

### Task A — Failure Risk Probability
* **Objective**: Predict the probability that component $c$ of vehicle $v$ will fail within a defined forecast horizon $H$ (in days):
  $$P(Y_{v,c,t} = 1 \mid \mathcal{I}_t)$$
  Where $\mathcal{I}_t$ represents all information available at prediction timestamp $t$, and $Y_{v,c,t}$ is a binary indicator of failure within the interval $[t, t+H]$.
* **Forecast Horizon Selection**: We set the primary horizon **$H = 14$ days**. This is justified because it matches the median supplier lead time across key critical parts, giving the warehouse team a complete action cycle to place orders and receive parts before a wear-out boundary triggers a catastrophic failure event.

### Task B — Parts Demand Forecasting
* **Objective**: Estimate the future quantity of part $p$ required during the forecast window $[t, t+H]$ for horizons $H \in \{7, 30, 60, 90\}$ days.
* **Planned Maintenance Demand ($D_{planned}$)**: Sum of parts required for operationally known scheduled maintenance events $M(t, H)$ created at or before $t$ and scheduled to occur during $[t, t+H]$:
  $$D_{planned}(p, t, H) = \sum_{m \in M_{known}(t, H)} Q_{template}(p, m)$$
* **Failure-Driven Demand ($D_{failure}$)**: Probabilistic demand generated from predicted component failures using the Weibull competing-risks failure probabilities $P_{fail}(v, c, t, H)$ estimated at timestamp $t$:
  $$E[D_{failure}(p, t, H)] = \sum_{v \in \text{Fleet}} \sum_{c \in C_v} P_{fail}(v, c, t, H) \times Q_{failure}(p \mid c)$$
* **Total Expected Demand**:
  $$E[D_{total}(p, t, H)] = D_{planned}(p, t, H) + E[D_{failure}(p, t, H)]$$

### Task C — Parts Availability (Stockout) Risk
* **Objective**: Estimate the probability that part $p$ will be unavailable at the moment it is demanded within $[t, t+H]$.
* **Distinction**: Demand forecasting (Task B) measures the *volume* of parts consumed over a period. Stockout risk (Task C) is the *probability of depletion* ($\text{Stock} < \text{Demand}$), incorporating initial stock on hand ($I_{hand}$), stock currently in transit ($I_{order}$), and the timing of arrivals relative to demand events.
* **Mathematical Formula**:
  $$P(\text{Stockout}_p) = P\left(\sum_{\tau = t}^{t+L_p} D_{total}(p, \tau) > I_{hand} + I_{order}(\tau)\right)$$
  Where $L_p$ is the supplier lead time for part $p$.

---

## 2. Statistical Uncertainty Framework

MinePulse AI quantifies forecast uncertainty using prediction quantiles ($P_{10}$ and $P_{95}$ forecast intervals), explicitly avoiding invalid "confidence interval" terminology.

### A. Model Selection for Predictive Distribution & Dispersion
For each part $p$, the system dynamically selects the dispersion model based on historical usage observations $\le t$:
1. **Overdispersed Usage (Negative Binomial)**: If variance exceeds 1.2 times the mean ($\text{Var}(D) > 1.2 \times E[D]$), the system selects the **Negative Binomial** dispersion model.
2. **Standard Usage (Poisson)**: If variance is comparable to mean ($\text{Var}(D) \approx E[D]$), the system selects the **Poisson** distribution model.
3. **Sparse Data Fallback (Sparse Bootstrap)**: If total historical usage observations $N < 5$, the model defaults to a conservative **Empirical Bootstrap** interval and flags the prediction as `SPARSE_HISTORY`.

### B. Empirical Interval Coverage & Pinball Loss Evaluation
Evaluators measure out-of-sample forecast quantile calibration using the **Pinball Loss (Quantile Loss)** function for quantile $q \in \{0.10, 0.95\}$:
$$\mathcal{L}_q(y, \hat{y}_q) = \max\left(q(y - \hat{y}_q), (q - 1)(y - \hat{y}_q)\right)$$
* **Metrics Reported**: MAE, RMSE, Pinball Loss ($P_{10}, P_{95}$), and Average Forecast Interval Width ($\hat{y}_{0.95} - \hat{y}_{0.10}$).

---

## 3. Inventory Optimization Function

The ordering decision is formalized as an expected cost minimization problem over the lead time $L_p$.

### Mathematical Objective Function
For each part $p$ at prediction timestamp $t$, find the recommended order quantity $Q^* \ge 0$ to minimize the expected total cost $E[C(Q)]$:

$$\min_{Q \ge 0} \quad E[C(Q)] = C_{order} \cdot \mathbb{I}(Q > 0) + C_{hold} \cdot E[I_{end}(Q)] + C_{down} \cdot E[S_{out}(Q)]$$

Subject to:
* $Q \ge MOQ$ (Minimum Order Quantity constraint, if $Q > 0$).
* $Q$ is an integer.

Where:
* $C_{order}$ is the fixed cost of placing an order.
* $C_{hold}$ is the holding cost per unit per day.
* $C_{down}$ is the downtime cost per vehicle-hour.
* $E[I_{end}(Q)]$ is the expected ending inventory on hand at $t+L_p$:
  $$E[I_{end}(Q)] = E\left[ \max(0, I_{hand} + I_{order} + Q - D_{total}) \right]$$
* $E[S_{out}(Q)]$ is the expected stockout quantity leading to downtime:
  $$E[S_{out}(Q)] = E\left[ \max(0, D_{total} - (I_{hand} + I_{order} + Q)) \right]$$

### Operational Output
The optimal quantity $Q^*$ is generated. If $Q^* > 0$, action required is set to `ORDER NOW`. If $Q^* = 0$ but $P(\text{Stockout}_p) > 0.15$, action is set to `MONITOR`.
