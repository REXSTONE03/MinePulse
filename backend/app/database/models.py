from sqlalchemy import create_engine, Column, Integer, Float, String, Boolean, ForeignKey, UniqueConstraint, Index, DateTime, CheckConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Vehicle(Base):
    __tablename__ = 'vehicles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    model = Column(String, nullable=False)  # e.g., CAT 797F, Komatsu PC8000
    age_years = Column(Float, nullable=False)
    operating_hours = Column(Float, default=0.0, nullable=False)
    status = Column(String, default='ACTIVE', nullable=False) # ACTIVE, DOWN, MAINTENANCE
    
    __table_args__ = (
        CheckConstraint(status.in_(['ACTIVE', 'DOWN', 'MAINTENANCE']), name='check_vehicle_status'),
        CheckConstraint(age_years >= 0, name='check_vehicle_age'),
        CheckConstraint(operating_hours >= 0, name='check_vehicle_hours'),
    )
    
    telemetry = relationship("VehicleTelemetry", back_populates="vehicle", cascade="all, delete-orphan")
    components = relationship("Component", back_populates="vehicle", cascade="all, delete-orphan")
    failures = relationship("Failure", back_populates="vehicle")
    maintenance_plans = relationship("MaintenancePlan", back_populates="vehicle")
    part_usage = relationship("PartUsage", back_populates="vehicle")

class VehicleTelemetry(Base):
    __tablename__ = 'vehicle_telemetry'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    operating_hours = Column(Float, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('vehicle_id', 'date', name='uq_vehicle_date'),
        Index('idx_telemetry_vehicle_date', 'vehicle_id', 'date'),
        CheckConstraint(operating_hours >= 0, name='check_telemetry_hours'),
    )
    
    vehicle = relationship("Vehicle", back_populates="telemetry")

class Component(Base):
    __tablename__ = 'components'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    type = Column(String, nullable=False)  # ENGINE, TRANSMISSION, HYDRAULICS, UNDERCARRIAGE
    installed_date = Column(String, nullable=False)  # YYYY-MM-DD
    operating_hours_at_install = Column(Float, default=0.0, nullable=False)
    current_hours = Column(Float, default=0.0, nullable=False)
    
    __table_args__ = (
        CheckConstraint(type.in_(['ENGINE', 'TRANSMISSION', 'HYDRAULICS', 'UNDERCARRIAGE']), name='check_component_type'),
        CheckConstraint(operating_hours_at_install >= 0, name='check_comp_hours_install'),
        CheckConstraint(current_hours >= 0, name='check_comp_current_hours'),
        Index('idx_components_vehicle', 'vehicle_id'),
    )
    
    vehicle = relationship("Vehicle", back_populates="components")
    failures = relationship("Failure", back_populates="component")
    maintenance_plans = relationship("MaintenancePlan", back_populates="component")

class Supplier(Base):
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    base_lead_time_days = Column(Integer, nullable=False)
    reliability_rate = Column(Float, nullable=False)
    
    __table_args__ = (
        CheckConstraint(base_lead_time_days > 0, name='check_supplier_lead_time'),
        CheckConstraint(reliability_rate >= 0.0, name='check_supplier_reliability'),
        CheckConstraint(reliability_rate <= 1.0, name='check_supplier_reliability_max'),
    )
    
    parts = relationship("Part", back_populates="supplier")

class Part(Base):
    __tablename__ = 'parts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    part_number = Column(String, unique=True, nullable=False)
    unit_cost = Column(Float, nullable=False)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    min_order_qty = Column(Integer, default=1, nullable=False)
    min_stock_level = Column(Integer, default=0, nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    
    __table_args__ = (
        CheckConstraint(unit_cost >= 0, name='check_part_cost'),
        CheckConstraint(min_order_qty > 0, name='check_part_moq'),
        CheckConstraint(min_stock_level >= 0, name='check_part_min_stock'),
        CheckConstraint(lead_time_days > 0, name='check_part_lead_time'),
        Index('idx_parts_supplier', 'supplier_id'),
    )
    
    supplier = relationship("Supplier", back_populates="parts")
    inventory = relationship("Inventory", back_populates="part", uselist=False, cascade="all, delete-orphan")
    part_usage = relationship("PartUsage", back_populates="part")
    recommendations = relationship("Recommendation", back_populates="part")
    purchase_orders = relationship("PurchaseOrder", back_populates="part")
    ledger_entries = relationship("InventoryLedger", back_populates="part", cascade="all, delete-orphan")

class PurchaseOrder(Base):
    __tablename__ = 'purchase_orders'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(Integer, ForeignKey('parts.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    order_date = Column(String, nullable=False)  # YYYY-MM-DD
    expected_delivery_date = Column(String, nullable=False)  # YYYY-MM-DD
    actual_delivery_date = Column(String, nullable=True)     # YYYY-MM-DD
    status = Column(String, default='PLACED', nullable=False)  # PLACED, DELIVERED
    
    __table_args__ = (
        CheckConstraint(quantity > 0, name='check_order_qty'),
        CheckConstraint(status.in_(['PLACED', 'DELIVERED']), name='check_order_status'),
        Index('idx_order_part', 'part_id'),
    )
    
    part = relationship("Part", back_populates="purchase_orders")

class InventoryLedger(Base):
    __tablename__ = 'inventory_ledger'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(Integer, ForeignKey('parts.id'), nullable=False)
    transaction_type = Column(String, nullable=False)  # INITIAL, USAGE, DELIVERY
    quantity = Column(Integer, nullable=False)          # positive for receipts, negative for consumption
    date = Column(String, nullable=False)              # YYYY-MM-DD
    reference_id = Column(Integer, nullable=True)      # links to purchase_orders.id or part_usage.id
    
    __table_args__ = (
        CheckConstraint(transaction_type.in_(['INITIAL', 'USAGE', 'DELIVERY']), name='check_ledger_type'),
        Index('idx_ledger_part_date', 'part_id', 'date'),
    )
    
    part = relationship("Part", back_populates="ledger_entries")

class Inventory(Base):
    __tablename__ = 'inventory'
    
    part_id = Column(Integer, ForeignKey('parts.id', ondelete='CASCADE'), primary_key=True)
    stock_on_hand = Column(Integer, default=0, nullable=False)
    stock_on_order = Column(Integer, default=0, nullable=False)
    stock_allocated = Column(Integer, default=0, nullable=False)
    
    __table_args__ = (
        CheckConstraint(stock_on_hand >= 0, name='check_stock_on_hand'),
        CheckConstraint(stock_on_order >= 0, name='check_stock_on_order'),
        CheckConstraint(stock_allocated >= 0, name='check_stock_allocated'),
    )
    
    part = relationship("Part", back_populates="inventory")

class MaintenanceTemplate(Base):
    __tablename__ = 'maintenance_templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    maintenance_type = Column(String, nullable=False)  # e.g., PM250, PM500, PM1000
    component_type = Column(String, nullable=False)    # ENGINE, TRANSMISSION, etc.
    part_id = Column(Integer, ForeignKey('parts.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('maintenance_type', 'component_type', 'part_id', name='uq_maint_template'),
        CheckConstraint(quantity > 0, name='check_template_qty'),
        CheckConstraint(component_type.in_(['ENGINE', 'TRANSMISSION', 'HYDRAULICS', 'UNDERCARRIAGE']), name='check_template_comp_type'),
    )

class MaintenancePlan(Base):
    __tablename__ = 'maintenance_plans'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id', ondelete='CASCADE'), nullable=False)
    component_id = Column(Integer, ForeignKey('components.id'), nullable=False)
    description = Column(String, nullable=False)  # e.g., PM250, PM500
    scheduled_date = Column(String, nullable=False)  # YYYY-MM-DD
    scheduled_hours = Column(Float, nullable=False)
    original_scheduled_date = Column(String, nullable=True) # For reschedule tracking
    rescheduled_reason = Column(String, nullable=True)
    rescheduled_timestamp = Column(String, nullable=True) # ISO DateTime
    status = Column(String, default='PENDING', nullable=False)  # PENDING, COMPLETED, RESCHEDULED
    
    __table_args__ = (
        CheckConstraint(status.in_(['PENDING', 'COMPLETED', 'RESCHEDULED']), name='check_maint_status'),
        CheckConstraint(scheduled_hours >= 0, name='check_maint_hours'),
        Index('idx_maint_vehicle', 'vehicle_id'),
        Index('idx_maint_component', 'component_id'),
        Index('idx_maint_scheduled_date', 'scheduled_date'),
    )
    
    vehicle = relationship("Vehicle", back_populates="maintenance_plans")
    component = relationship("Component", back_populates="maintenance_plans")
    part_usage = relationship("PartUsage", back_populates="maintenance_plan")

class Failure(Base):
    __tablename__ = 'failures'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), nullable=False)
    component_id = Column(Integer, ForeignKey('components.id'), nullable=False)
    part_id = Column(Integer, ForeignKey('parts.id'), nullable=True) # Primary failed part
    failure_date = Column(String, nullable=False)  # YYYY-MM-DD
    operating_hours = Column(Float, nullable=False)
    downtime_hours = Column(Float, default=0.0, nullable=False)
    severity = Column(String, default='MINOR', nullable=False)  # CATASTROPHIC, MINOR
    resolved = Column(Boolean, default=False, nullable=False)
    scenario_id = Column(String, nullable=False, default='SCENARIO_NORMAL_WEAR')
    
    __table_args__ = (
        CheckConstraint(severity.in_(['CATASTROPHIC', 'MINOR']), name='check_failure_severity'),
        CheckConstraint(operating_hours >= 0, name='check_failure_hours'),
        CheckConstraint(downtime_hours >= 0, name='check_failure_downtime'),
        Index('idx_failures_vehicle', 'vehicle_id'),
        Index('idx_failures_component', 'component_id'),
        Index('idx_failures_date', 'failure_date'),
    )
    
    vehicle = relationship("Vehicle", back_populates="failures")
    component = relationship("Component", back_populates="failures")
    part_usage = relationship("PartUsage", back_populates="failure")

class PartUsage(Base):
    __tablename__ = 'part_usage'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey('vehicles.id'), nullable=False)
    part_id = Column(Integer, ForeignKey('parts.id'), nullable=False)
    maintenance_plan_id = Column(Integer, ForeignKey('maintenance_plans.id'), nullable=True)
    failure_id = Column(Integer, ForeignKey('failures.id'), nullable=True)
    quantity = Column(Integer, nullable=False)
    usage_date = Column(String, nullable=False)  # YYYY-MM-DD
    
    __table_args__ = (
        CheckConstraint(quantity > 0, name='check_usage_qty'),
        CheckConstraint(
            '((maintenance_plan_id IS NOT NULL AND failure_id IS NULL) OR (maintenance_plan_id IS NULL AND failure_id IS NOT NULL))',
            name='check_usage_source'
        ),
        Index('idx_usage_vehicle', 'vehicle_id'),
        Index('idx_usage_part', 'part_id'),
        Index('idx_usage_date', 'usage_date'),
    )
    
    vehicle = relationship("Vehicle", back_populates="part_usage")
    part = relationship("Part", back_populates="part_usage")
    maintenance_plan = relationship("MaintenancePlan", back_populates="part_usage")
    failure = relationship("Failure", back_populates="part_usage")

class ModelGovernance(Base):
    __tablename__ = 'model_governance'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_version = Column(String, nullable=False)
    algorithm_name = Column(String, nullable=False)
    feature_set_version = Column(String, nullable=False)
    training_dataset_version = Column(String, nullable=False)
    training_timestamp = Column(String, nullable=False)  # ISO8601
    hyperparameters = Column(String, nullable=False)       # JSON string
    metrics_serialized = Column(String, nullable=False)    # JSON string
    is_active = Column(Boolean, default=True, nullable=False)
    
    recommendations = relationship("Recommendation", back_populates="model_governance")

class Recommendation(Base):
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    part_id = Column(Integer, ForeignKey('parts.id'), nullable=False)
    model_governance_id = Column(Integer, ForeignKey('model_governance.id'), nullable=False)
    expected_demand = Column(Float, nullable=False)
    p50_demand = Column(Float, nullable=False)
    p80_demand = Column(Float, nullable=False)
    p95_demand = Column(Float, nullable=False)
    current_inventory = Column(Integer, nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    recommended_order_qty = Column(Integer, default=0, nullable=False)
    action_required = Column(String, nullable=False)  # ORDER NOW, MONITOR, NORMAL
    status = Column(String, default='PENDING', nullable=False)  # PENDING, APPROVED, OVERRIDDEN
    created_date = Column(String, nullable=False)  # YYYY-MM-DD
    
    __table_args__ = (
        CheckConstraint(action_required.in_(['ORDER NOW', 'MONITOR', 'NORMAL']), name='check_rec_action'),
        CheckConstraint(status.in_(['PENDING', 'APPROVED', 'OVERRIDDEN']), name='check_rec_status'),
        CheckConstraint(recommended_order_qty >= 0, name='check_rec_qty'),
        Index('idx_rec_part', 'part_id'),
    )
    
    part = relationship("Part", back_populates="recommendations")
    model_governance = relationship("ModelGovernance", back_populates="recommendations")
    override = relationship("Override", back_populates="recommendation", uselist=False)

class Override(Base):
    __tablename__ = 'overrides'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(Integer, ForeignKey('recommendations.id'), nullable=False)
    part_id = Column(Integer, ForeignKey('parts.id'), nullable=False)
    dispatcher_name = Column(String, nullable=False)
    original_recommendation = Column(String, nullable=False)  # JSON snapshot
    new_decision = Column(String, nullable=False)             # ORDER NOW, MONITOR, NORMAL
    override_qty = Column(Integer, nullable=False)
    reason = Column(String, nullable=False)
    timestamp = Column(String, nullable=False)                 # ISO8601
    
    __table_args__ = (
        CheckConstraint(override_qty >= 0, name='check_override_qty'),
        Index('idx_override_recommendation', 'recommendation_id'),
    )
    
    recommendation = relationship("Recommendation", back_populates="override")

class AuditLog(Base):
    __tablename__ = 'audit_log'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String, nullable=False)  # ISO8601
    user = Column(String, nullable=False)
    action = Column(String, nullable=False)      # e.g., OVERRIDE_APPLIED
    details = Column(String, nullable=False)     # JSON string
    
    __table_args__ = (
        Index('idx_audit_timestamp', 'timestamp'),
    )

class ExperimentRegistry(Base):
    __tablename__ = 'experiment_registry'
    
    id = Column(String, primary_key=True)  # unique string id e.g. EXP-2026-001
    dataset_version = Column(String, nullable=False)
    random_seed = Column(Integer, nullable=False)
    training_start = Column(String, nullable=False)
    training_end = Column(String, nullable=False)
    validation_start = Column(String, nullable=False)
    validation_end = Column(String, nullable=False)
    test_start = Column(String, nullable=False)
    test_end = Column(String, nullable=False)
    failure_model = Column(String, nullable=False)
    demand_model = Column(String, nullable=False)
    forecast_horizon = Column(Integer, nullable=False)
    uncertainty_method = Column(String, nullable=False)
    inventory_policy = Column(String, nullable=False)
    baseline_policy = Column(String, nullable=False)
    model_parameters = Column(String, nullable=False)  # JSON string
    results_serialized = Column(String, nullable=True) # JSON string
    
    __table_args__ = (
        Index('idx_experiment_seed', 'random_seed'),
    )
