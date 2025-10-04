# app/crud.py
from fastapi import HTTPException, status, Depends
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date, timedelta
import uuid
import json
from .auth import get_current_user
from app.firebase_init import db_ref, storage_bucket, auth_client
from .models import (
    UserRole, UnitStatus, MaintenanceStatus, PaymentStatus, UrgencyLevel,
    UserCreate, UserResponse, TenantProfile, MaintenanceRequest, 
    MaintenanceRequestCreate, MaintenanceRequestUpdate, MaintenanceUpdate,
    Payment, PaymentCreate, Property, PropertyCreate, Unit, UnitCreate,
    LeaseInfo, Notification, NotificationCreate, ReportRequest, KPIStats
)

class CRUD:
    # ===== helper =====
    @staticmethod
    def _ensure_db():
        if db_ref is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database not initialized (db_ref is None). Check Firebase credentials and FIREBASE_DB_URL."
            )

    # ===== DASHBOARD OPERATIONS =====
    @staticmethod
    async def get_user_dashboard(user_id: str, user_role: UserRole) -> Dict[str, Any]:
        CRUD._ensure_db()
        try:
            dashboard_data = {}
            
            # Get tenant profile
            tenant_ref = db_ref.child(f'tenants/{user_id}')
            tenant_data = tenant_ref.get() or {}
            dashboard_data['profile'] = tenant_data.get('personal_info', {})
            
            # Get lease info
            dashboard_data['lease'] = tenant_data.get('lease_info', {})
            
            # Get recent maintenance requests (last 5)
            requests_ref = db_ref.child('maintenance_requests')
            user_requests = requests_ref.order_by_child('tenant_id').equal_to(user_id)\
                                      .limit_to_last(5).get() or {}
            dashboard_data['maintenance_requests'] = [
                {'id': req_id, **req_data} for req_id, req_data in (user_requests.items() if isinstance(user_requests, dict) else [])
            ]
            
            # Get payment status
            payments_ref = db_ref.child('payments')
            user_payments = payments_ref.order_by_child('tenant_id').equal_to(user_id)\
                                      .limit_to_last(3).get() or {}
            dashboard_data['payments'] = [
                {'id': pay_id, **pay_data} for pay_id, pay_data in (user_payments.items() if isinstance(user_payments, dict) else [])
            ]
            
            # Calculate upcoming rent due
            if tenant_data.get('lease_info') and tenant_data['lease_info'].get('rent_amount'):
                today = datetime.now()
                next_month = (today.replace(day=1) + timedelta(days=32))
                first_of_month = next_month.replace(day=1)
                
                dashboard_data['upcoming_rent'] = {
                    'amount': tenant_data['lease_info']['rent_amount'],
                    'due_date': first_of_month.isoformat(),
                    'days_until_due': (first_of_month - today).days
                }
            
            # Get unread notifications count
            notif_ref = db_ref.child(f'notifications/{user_id}')
            notifications = notif_ref.get() or {}
            unread_count = sum(1 for notif in notifications.values() if not notif.get('read', False)) if isinstance(notifications, dict) else 0
            dashboard_data['unread_notifications'] = unread_count
            
            return dashboard_data
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error loading user dashboard: {str(e)}"
            )

    @staticmethod
    async def get_staff_dashboard(staff_id: str) -> Dict[str, Any]:
        CRUD._ensure_db()
        try:
            dashboard_data = {}
            
            # Get assigned maintenance tasks
            requests_ref = db_ref.child('maintenance_requests')
            assigned_requests = requests_ref.order_by_child('assigned_to').equal_to(staff_id).get() or {}
            
            # Filter by status
            open_requests = {k: v for k, v in assigned_requests.items() 
                           if v.get('status') in ['submitted', 'in_progress']} if isinstance(assigned_requests, dict) else {}
            resolved_requests = {k: v for k, v in assigned_requests.items() 
                               if v.get('status') in ['resolved', 'closed']} if isinstance(assigned_requests, dict) else {}
            
            dashboard_data['assigned_tasks'] = {
                'open': [{'id': req_id, **req_data} for req_id, req_data in open_requests.items()],
                'resolved': [{'id': req_id, **req_data} for req_id, req_data in resolved_requests.items()],
                'total_open': len(open_requests),
                'total_resolved': len(resolved_requests)
            }
            
            # Get recent activity (tasks updated in last 7 days)
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_activity = {}
            for req_id, req_data in (assigned_requests.items() if isinstance(assigned_requests, dict) else []):
                if req_data.get('updated_at', '') >= week_ago:
                    recent_activity[req_id] = req_data
            
            dashboard_data['recent_activity'] = [
                {'id': req_id, **req_data} for req_id, req_data in recent_activity.items()
            ]
            
            # Get performance metrics
            completed_this_month = sum(1 for req in (assigned_requests.values() if isinstance(assigned_requests, dict) else []) 
                                     if req.get('status') in ['resolved', 'closed'] and
                                     req.get('updated_at', '').startswith(datetime.now().strftime('%Y-%m')))
            
            dashboard_data['performance'] = {
                'tasks_completed_month': completed_this_month,
                'total_assigned': len(assigned_requests) if isinstance(assigned_requests, dict) else 0,
                'completion_rate': (completed_this_month / len(assigned_requests) * 100) if assigned_requests and isinstance(assigned_requests, dict) else 0
            }
            
            return dashboard_data
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error loading staff dashboard: {str(e)}"
            )

    @staticmethod
    async def get_admin_dashboard() -> Dict[str, Any]:
        CRUD._ensure_db()
        try:
            dashboard_data = {}
            
            # Get all properties and units
            properties_ref = db_ref.child('properties')
            properties = properties_ref.get() or {}
            
            # Calculate occupancy rates and rent statistics
            total_units = 0
            occupied_units = 0
            total_rent = 0
            collected_rent = 0
            
            for prop_id, prop_data in (properties.items() if isinstance(properties, dict) else []):
                units = prop_data.get('units', {})
                total_units += len(units) if isinstance(units, dict) else 0
                occupied_units += sum(1 for unit in (units.values() if isinstance(units, dict) else []) 
                                    if unit.get('status') == 'occupied')
                
                # Get rent data for occupied units
                for unit_id, unit_data in (units.items() if isinstance(units, dict) else []):
                    if unit_data.get('status') == 'occupied':
                        # Find tenant for this unit and get rent amount
                        tenants_ref = db_ref.child('tenants')
                        # The query below assumes you stored lease_info with unit_id value
                        tenants = tenants_ref.order_by_child('lease_info/unit_id').equal_to(unit_id).get() or {}
                        for tenant_id, tenant_data in (tenants.items() if isinstance(tenants, dict) else []):
                            if tenant_data.get('lease_info', {}).get('unit_id') == unit_id:
                                rent_amount = tenant_data['lease_info'].get('rent_amount', 0)
                                total_rent += rent_amount
                                break
            
            # Get payments for current month
            current_month = datetime.now().strftime('%Y-%m')
            payments_ref = db_ref.child('payments')
            all_payments = payments_ref.get() or {}
            
            monthly_payments = []
            for pay_id, pay_data in (all_payments.items() if isinstance(all_payments, dict) else []):
                if pay_data.get('paid_date', '').startswith(current_month) and pay_data.get('status') == 'paid':
                    monthly_payments.append(pay_data)
                    collected_rent += pay_data.get('amount', 0)
            
            # Get maintenance stats
            requests_ref = db_ref.child('maintenance_requests')
            all_requests = requests_ref.get() or {}
            
            open_requests = sum(1 for req in (all_requests.values() if isinstance(all_requests, dict) else []) 
                              if req.get('status') in ['submitted', 'in_progress'])
            resolved_this_month = sum(1 for req in (all_requests.values() if isinstance(all_requests, dict) else []) 
                                    if req.get('status') in ['resolved', 'closed'] and
                                    req.get('updated_at', '').startswith(current_month))
            
            dashboard_data['overview'] = {
                'total_properties': len(properties) if isinstance(properties, dict) else 0,
                'total_units': total_units,
                'occupied_units': occupied_units,
                'vacancy_rate': ((total_units - occupied_units) / total_units * 100) if total_units else 0,
                'occupancy_rate': (occupied_units / total_units * 100) if total_units else 0,
                'total_monthly_rent': total_rent,
                'rent_collected_this_month': collected_rent,
                'collection_rate': (collected_rent / total_rent * 100) if total_rent else 0,
                'open_maintenance_requests': open_requests,
                'resolved_this_month': resolved_this_month
            }
            
            # Get recent activities
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            recent_activities = []
            
            # Recent payments
            for pay_id, pay_data in (all_payments.items() if isinstance(all_payments, dict) else []):
                if pay_data.get('paid_date', '') >= week_ago:
                    recent_activities.append({
                        'type': 'payment',
                        'id': pay_id,
                        'data': pay_data,
                        'timestamp': pay_data.get('paid_date')
                    })
            
            # Recent maintenance requests
            for req_id, req_data in (all_requests.items() if isinstance(all_requests, dict) else []):
                if req_data.get('created_at', '') >= week_ago:
                    recent_activities.append({
                        'type': 'maintenance',
                        'id': req_id,
                        'data': req_data,
                        'timestamp': req_data.get('created_at')
                    })
            
            # Sort by timestamp and take last 10
            recent_activities.sort(key=lambda x: x['timestamp'] or "", reverse=True)
            dashboard_data['recent_activities'] = recent_activities[:10]
            
            # Get financial KPIs
            dashboard_data['financials'] = await CRUD._calculate_financial_kpis()
            
            return dashboard_data
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error loading admin dashboard: {str(e)}"
            )

    # ===== PROPERTY & UNIT MANAGEMENT =====
    @staticmethod
    async def create_property(property_data: PropertyCreate) -> Property:
        CRUD._ensure_db()
        try:
            property_id = str(uuid.uuid4())
            property_ref = db_ref.child('properties').child(property_id)
            
            property_obj = Property(
                id=property_id,
                **property_data.dict(),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            property_ref.set(property_obj.__dict__)
            return property_obj
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating property: {str(e)}"
            )

    @staticmethod
    async def get_properties(
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> List[Property]:
        CRUD._ensure_db()
        try:
            properties = db_ref.child('properties').get() or {}
            
            properties_list = []
            for prop_id, prop_data in (properties.items() if isinstance(properties, dict) else []):
                property_obj = Property(id=prop_id, **prop_data)
                
                # Apply filters
                if filters:
                    matches = True
                    for key, value in filters.items():
                        if getattr(property_obj, key, None) != value:
                            matches = False
                            break
                    if not matches:
                        continue
                
                # Apply search
                if search:
                    search_lower = search.lower()
                    if (search_lower not in (property_obj.name or "").lower() and
                        search_lower not in (property_obj.address or "").lower() and
                        search_lower not in (property_obj.city or "").lower()):
                        continue
                
                properties_list.append(property_obj)
            
            return properties_list
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving properties: {str(e)}"
            )

    @staticmethod
    async def add_unit_to_property(property_id: str, unit_data: UnitCreate) -> Unit:
        CRUD._ensure_db()
        try:
            # Verify property exists
            property_ref = db_ref.child('properties').child(property_id)
            if not property_ref.get():
                raise HTTPException(status_code=404, detail="Property not found")
            
            unit_id = f"{property_id}_{unit_data.unit_number}"
            unit_ref = db_ref.child('properties').child(property_id).child('units').child(unit_id)
            
            unit_obj = Unit(
                id=unit_id,
                property_id=property_id,
                **unit_data.dict(),
                status=UnitStatus.VACANT,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            unit_ref.set(unit_obj.__dict__)
            return unit_obj
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error adding unit: {str(e)}"
            )

    @staticmethod
    async def get_units(
        property_id: Optional[str] = None,
        status: Optional[UnitStatus] = None
    ) -> List[Unit]:
        CRUD._ensure_db()
        try:
            units_list = []
            
            if property_id:
                # Get units for specific property
                units = db_ref.child('properties').child(property_id).child('units').get() or {}
                for unit_id, unit_data in (units.items() if isinstance(units, dict) else []):
                    if status and unit_data.get('status') != status.value:
                        continue
                    units_list.append(Unit(id=unit_id, property_id=property_id, **unit_data))
            else:
                # Get all units across all properties
                properties = db_ref.child('properties').get() or {}
                for prop_id, prop_data in (properties.items() if isinstance(properties, dict) else []):
                    units = prop_data.get('units', {}) or {}
                    for unit_id, unit_data in (units.items() if isinstance(units, dict) else []):
                        if status and unit_data.get('status') != status.value:
                            continue
                        units_list.append(Unit(id=unit_id, property_id=prop_id, **unit_data))
            
            return units_list
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving units: {str(e)}"
            )

    # ===== TENANT MANAGEMENT =====
    @staticmethod
    async def get_tenants(
        property_id: Optional[str] = None,
        unit_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        CRUD._ensure_db()
        try:
            all_tenants = db_ref.child('tenants').get() or {}
            
            tenants_list = []
            for tenant_id, tenant_data in (all_tenants.items() if isinstance(all_tenants, dict) else []):
                lease_info = tenant_data.get('lease_info', {})
                
                # Apply filters
                if property_id and lease_info.get('unit_id', '').split('_')[0] != property_id:
                    continue
                if unit_id and lease_info.get('unit_id') != unit_id:
                    continue
                
                # Get user info
                user_data = db_ref.child('users').child(tenant_id).get() or {}
                
                tenant_info = {
                    'id': tenant_id,
                    'user_info': user_data,
                    'profile': tenant_data.get('personal_info', {}),
                    'lease': lease_info,
                    'maintenance_requests': tenant_data.get('maintenance_requests', {}),
                    'documents': tenant_data.get('documents', {})
                }
                tenants_list.append(tenant_info)
            
            return tenants_list
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error retrieving tenants: {str(e)}"
            )

    @staticmethod
    async def upload_lease_document(
        tenant_id: str, 
        file_data: bytes, 
        filename: str,
        lease_info: LeaseInfo
    ) -> Dict[str, Any]:
        CRUD._ensure_db()
        try:
            # Upload to Firebase Storage
            if not storage_bucket:
                raise HTTPException(status_code=500, detail="Storage bucket not configured")
            bucket = storage_bucket
            blob = bucket.blob(f'leases/{tenant_id}/{filename}')
            blob.upload_from_string(file_data, content_type='application/pdf')
            blob.make_public()
            
            # Update tenant lease info
            lease_ref = db_ref.child(f'tenants/{tenant_id}/lease_info')
            lease_data = {
                **lease_info.dict(),
                'lease_document_url': blob.public_url,
                'document_upload_date': datetime.now().isoformat()
            }
            lease_ref.set(lease_data)
            
            # Update unit status to occupied
            if lease_info.unit_id:
                unit_parts = lease_info.unit_id.split('_')
                if len(unit_parts) == 2:
                    prop_id, unit_num = unit_parts
                    db_ref.child('properties').child(prop_id).child('units').child(lease_info.unit_id).child('status').set(UnitStatus.OCCUPIED.value)
            
            return {
                'document_url': blob.public_url,
                'lease_info': lease_data
            }
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error uploading lease document: {str(e)}"
            )

    # ===== RENT & PAYMENTS =====
    @staticmethod
    async def get_rent_due_report() -> List[Dict[str, Any]]:
        CRUD._ensure_db()
        try:
            all_tenants = db_ref.child('tenants').get() or {}
            all_payments = db_ref.child('payments').get() or {}
            
            rent_due_report = []
            today = datetime.now().date()
            
            for tenant_id, tenant_data in (all_tenants.items() if isinstance(all_tenants, dict) else []):
                lease_info = tenant_data.get('lease_info', {})
                if not lease_info:
                    continue
                
                rent_amount = lease_info.get('rent_amount', 0)
                unit_id = lease_info.get('unit_id')
                
                # Get payment history for this tenant
                tenant_payments = {}
                for pay_id, pay_data in (all_payments.items() if isinstance(all_payments, dict) else []):
                    if pay_data.get('tenant_id') == tenant_id:
                        tenant_payments[pay_id] = pay_data
                
                # Calculate overdue amount
                overdue_amount = 0
                for payment in tenant_payments.values():
                    if (payment.get('status') == 'overdue' or 
                        (payment.get('status') == 'pending' and 
                         datetime.fromisoformat(payment['due_date']).date() < today)):
                        overdue_amount += payment.get('amount', 0)
                
                rent_due_report.append({
                    'tenant_id': tenant_id,
                    'tenant_name': tenant_data.get('personal_info', {}).get('full_name'),
                    'unit_id': unit_id,
                    'monthly_rent': rent_amount,
                    'overdue_amount': overdue_amount,
                    'payment_history': list(tenant_payments.values())
                })
            
            return rent_due_report
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating rent due report: {str(e)}"
            )

    # ===== MAINTENANCE TASK MANAGEMENT =====
    @staticmethod
    async def assign_maintenance_task(
        request_id: str, 
        staff_id: str, 
        priority: str = "medium"
    ) -> MaintenanceRequest:
        CRUD._ensure_db()
        try:
            request_ref = db_ref.child(f'maintenance_requests/{request_id}')
            request_data = request_ref.get()
            
            if not request_data:
                raise HTTPException(status_code=404, detail="Maintenance request not found")
            
            # Verify staff exists
            staff_data = db_ref.child(f'users/{staff_id}').get()
            if not staff_data or staff_data.get('role') != 'staff':
                raise HTTPException(status_code=404, detail="Staff member not found")
            
            # Update request
            updates = {
                'assigned_to': staff_id,
                'priority': priority,
                'status': MaintenanceStatus.IN_PROGRESS.value,
                'updated_at': datetime.now().isoformat()
            }
            
            for key, value in updates.items():
                request_ref.child(key).set(value)
            
            # Add update entry
            update_id = str(uuid.uuid4())
            update_data = {
                'message': f'Task assigned to staff member {staff_id}',
                'posted_by': 'system',
                'timestamp': datetime.now().isoformat()
            }
            request_ref.child(f'updates/{update_id}').set(update_data)
            
            # Create notification for staff
            await CRUD.create_notification(NotificationCreate(
                user_id=staff_id,
                type='task_assignment',
                title='New Maintenance Task Assigned',
                message=f'You have been assigned maintenance request: {request_data.get("title")}',
                deep_link=f'/maintenance/{request_id}'
            ))
            
            updated_data = request_ref.get()
            return MaintenanceRequest(id=request_id, **updated_data)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error assigning maintenance task: {str(e)}"
            )

    @staticmethod
    async def update_maintenance_status(
        request_id: str, 
        status: MaintenanceStatus,
        staff_id: str,
        notes: Optional[str] = None
    ) -> MaintenanceRequest:
        CRUD._ensure_db()
        try:
            request_ref = db_ref.child(f'maintenance_requests/{request_id}')
            request_data = request_ref.get()
            
            if not request_data:
                raise HTTPException(status_code=404, detail="Maintenance request not found")
            
            # Update status
            request_ref.child('status').set(status.value)
            request_ref.child('updated_at').set(datetime.now().isoformat())
            
            # Add update entry
            if notes:
                update_id = str(uuid.uuid4())
                update_data = {
                    'message': notes,
                    'posted_by': staff_id,
                    'timestamp': datetime.now().isoformat()
                }
                request_ref.child(f'updates/{update_id}').set(update_data)
            
            # Notify tenant if resolved
            if status in [MaintenanceStatus.RESOLVED, MaintenanceStatus.CLOSED]:
                tenant_id = request_data.get('tenant_id')
                await CRUD.create_notification(NotificationCreate(
                    user_id=tenant_id,
                    type='maintenance_update',
                    title='Maintenance Request Resolved',
                    message=f'Your maintenance request "{request_data.get("title")}" has been resolved.',
                    deep_link=f'/maintenance/{request_id}'
                ))
            
            updated_data = request_ref.get()
            return MaintenanceRequest(id=request_id, **updated_data)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error updating maintenance status: {str(e)}"
            )

    # ===== REPORTS & ANALYTICS =====
    @staticmethod
    async def generate_report(report_type: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        CRUD._ensure_db()
        try:
            if report_type == 'financial':
                return await CRUD._generate_financial_report(filters)
            elif report_type == 'occupancy':
                return await CRUD._generate_occupancy_report(filters)
            elif report_type == 'maintenance':
                return await CRUD._generate_maintenance_report(filters)
            else:
                raise HTTPException(status_code=400, detail="Invalid report type")
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error generating report: {str(e)}"
            )

    @staticmethod
    async def get_kpi_stats() -> KPIStats:
        CRUD._ensure_db()
        try:
            # Calculate various KPIs
            properties = db_ref.child('properties').get() or {}
            
            total_units = 0
            occupied_units = 0
            vacant_units = 0
            total_rent = 0
            
            for prop_id, prop_data in (properties.items() if isinstance(properties, dict) else []):
                units = prop_data.get('units', {})
                total_units += len(units) if isinstance(units, dict) else 0
                for unit in (units.values() if isinstance(units, dict) else []):
                    if unit.get('status') == 'occupied':
                        occupied_units += 1
                    elif unit.get('status') == 'vacant':
                        vacant_units += 1
            
            # Get financial data
            payments = db_ref.child('payments').get() or {}
            
            current_month = datetime.now().strftime('%Y-%m')
            monthly_revenue = 0
            for payment in (payments.values() if isinstance(payments, dict) else []):
                if (payment.get('paid_date', '').startswith(current_month) and 
                    payment.get('status') == 'paid'):
                    monthly_revenue += payment.get('amount', 0)
            
            # Get maintenance costs (this would need actual cost data)
            requests = db_ref.child('maintenance_requests').get() or {}
            maintenance_costs = 0  # Placeholder
            
            return KPIStats(
                total_properties=len(properties) if isinstance(properties, dict) else 0,
                total_units=total_units,
                occupancy_rate=(occupied_units / total_units * 100) if total_units else 0,
                vacancy_rate=(vacant_units / total_units * 100) if total_units else 0,
                monthly_revenue=monthly_revenue,
                maintenance_costs=maintenance_costs,
                net_operating_income=monthly_revenue - maintenance_costs
            )
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error calculating KPI stats: {str(e)}"
            )

    # ===== PRIVATE HELPER METHODS =====
    @staticmethod
    async def _calculate_financial_kpis() -> Dict[str, Any]:
        # Implementation for financial calculations
        return {}

    @staticmethod
    async def _generate_financial_report(filters: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation for financial reports
        return {}

    @staticmethod
    async def _generate_occupancy_report(filters: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation for occupancy reports
        return {}

    @staticmethod
    async def _generate_maintenance_report(filters: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation for maintenance reports
        return {}

# Create global instance
crud = CRUD()
