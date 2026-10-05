from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

# Auth & User Schemas
class LoginRequest(BaseModel):
    username: str = Field(..., json_schema_extra={"example": "admin"})
    password: str = Field(..., json_schema_extra={"example": "admin123"})

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    expires_in_minutes: int

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool
    created_at: str

# Health Schema
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    service_status: str

# Prediction Schema
class PredictRequest(BaseModel):
    prediction_timestamp: str = Field(..., json_schema_extra={"example": "2025-06-01"})
    horizon_days: int = Field(30, json_schema_extra={"example": 30})

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
    prediction_timestamp: str = Field(..., json_schema_extra={"example": "2025-06-01"})
    horizon_days: int = Field(30, json_schema_extra={"example": 30})

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
    prediction_timestamp: str = Field(..., json_schema_extra={"example": "2025-06-01"})
    horizon_days: int = Field(30, json_schema_extra={"example": 30})

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
    dispatcher_name: str = Field(..., json_schema_extra={"example": "Dispatcher_John_Smith"})
    new_decision: str = Field(..., json_schema_extra={"example": "MONITOR"})
    override_qty: int = Field(0, json_schema_extra={"example": 0})
    reason: str = Field(..., json_schema_extra={"example": "Urgent shipment scheduled from alternative warehouse"})
    timestamp: Optional[str] = Field(None, json_schema_extra={"example": "2025-06-01T12:00:00"})

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

# Monitoring Schemas
class RetrainTriggerRequest(BaseModel):
    force: bool = Field(False, json_schema_extra={"example": False})

class RetrainTriggerResponse(BaseModel):
    status: str
    message: str
    event_details: Optional[dict] = None
    current_psi: Optional[float] = None
