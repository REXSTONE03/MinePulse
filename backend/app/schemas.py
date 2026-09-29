from pydantic import BaseModel, Field
from typing import List, Optional, Any

# Health Schema
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    service_status: str

# Prediction Schema
class PredictRequest(BaseModel):
    prediction_timestamp: str = Field(..., example="2025-06-01")
    horizon_days: int = Field(30, example=30)

class ComponentPredictionItem(BaseModel):
    component_id: int
    vehicle_id: int
    vehicle_name: str
    type: str
    current_hours: float
    operating_hours_at_install: float
    installed_date: str
    weibull_beta: float
    weibull_eta: float
    catastrophic_rate: float
    failure_probability_7d: float
    failure_probability_30d: float
    failure_probability_60d: float
    failure_probability_90d: float
    risk_tier: str

class PredictResponse(BaseModel):
    prediction_timestamp: str
    horizon_days: int
    total_components_evaluated: int
    component_predictions: List[ComponentPredictionItem]

# Forecast Schema
class ForecastRequest(BaseModel):
    prediction_timestamp: str = Field(..., example="2025-06-01")
    horizon_days: int = Field(30, example=30)

class PartForecastItem(BaseModel):
    part_id: int
    part_name: str
    part_number: str
    planned_maintenance_demand: float
    failure_driven_demand: float
    total_expected_demand: float
    p10_demand: float
    p95_demand: float
    confidence_flag: str
    dispersion_model: str

class ForecastResponse(BaseModel):
    prediction_timestamp: str
    horizon_days: int
    total_parts_evaluated: int
    forecasts: List[PartForecastItem]

# Recommendation Schema
class RecommendationRequest(BaseModel):
    prediction_timestamp: str = Field(..., example="2025-06-01")
    horizon_days: int = Field(30, example=30)

class InventoryRecommendationItem(BaseModel):
    recommendation_id: Optional[int] = None
    part_id: int
    part_name: str
    part_number: str
    expected_demand: float
    planned_demand: float
    failure_demand: float
    p10_demand: float
    p95_demand: float
    stock_on_hand: int
    stock_on_order: int
    stock_allocated: int
    available_inventory: int
    safety_stock: int
    projected_shortage: int
    lead_time_days: int
    unit_cost: float
    supplier_reliability: float
    max_component_risk: float
    recommended_order_qty: int
    action_required: str
    priority: str
    explanation: str
    status: Optional[str] = "PENDING"

class MaintenanceRecommendationItem(BaseModel):
    component_id: int
    vehicle_id: int
    component_type: str
    failure_probability: float
    risk_tier: str
    has_planned_pm: bool
    scheduled_pm_date: Optional[str] = None
    action: str
    priority: str
    reason: str

class RecommendationSummary(BaseModel):
    total_parts_analyzed: int
    urgent_reorders: int
    high_reorders: int
    critical_maintenance_components: int

class RecommendationResponse(BaseModel):
    prediction_timestamp: str
    horizon_days: int
    model_governance_id: int
    inventory_recommendations: List[InventoryRecommendationItem]
    maintenance_recommendations: List[MaintenanceRecommendationItem]
    summary: RecommendationSummary

# Dispatcher Override Schema
class OverrideRequest(BaseModel):
    dispatcher_name: str = Field(..., example="Dispatcher_John_Smith")
    new_decision: str = Field(..., example="MONITOR")
    override_qty: int = Field(0, example=0)
    reason: str = Field(..., example="Urgent shipment scheduled from alternative warehouse")
    timestamp: Optional[str] = Field(None, example="2025-06-01T12:00:00")

class OverrideResponse(BaseModel):
    status: str
    message: str
    recommendation: dict
    override_details: dict

# Audit Log Item
class AuditLogItem(BaseModel):
    id: int
    timestamp: str
    user: str
    action: str
    details: dict
