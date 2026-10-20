"""
LeaseAI - Anomaly Detection Engine
Phase 6: Agentic AI Layer

Detects and flags issues across the lease portfolio:
- Rent escalation mismatches
- Critical date deadlines approaching
- Low confidence field detection
- Expired leases still marked active
- Missing critical data
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from decimal import Decimal
import json


class AnomalyDetectionEngine:
    """
    Scans portfolio for anomalies and creates alerts
    """
    
    # Severity thresholds
    SEVERITY_THRESHOLDS = {
        'CRITICAL_DATE': {
            'CRITICAL': 7,   # 7 days or less
            'HIGH': 30,      # 30 days or less
            'MEDIUM': 60,    # 60 days or less
            'LOW': 90        # 90 days or less
        },
        'CONFIDENCE': {
            'CRITICAL': 5,   # 5+ low confidence fields
            'HIGH': 3,       # 3-4 low confidence fields
            'MEDIUM': 2,     # 2 low confidence fields
            'LOW': 1         # 1 low confidence field
        },
        'RENT_VARIANCE': {
            'CRITICAL': 1000,  # $1000+ variance
            'HIGH': 500,       # $500-999 variance
            'MEDIUM': 200,     # $200-499 variance
            'LOW': 100         # $100-199 variance
        }
    }
    
    def __init__(self, supabase_client):
        """Initialize anomaly detection engine"""
        self.sb = supabase_client
    
    def scan_portfolio(self, client_id: str = None) -> Dict:
        """
        Scan entire portfolio (or single client) for anomalies
        
        Args:
            client_id: Optional client UUID to scan specific portfolio
            
        Returns:
            Dictionary with scan results and detected anomalies
        """
        print("🔍 Starting portfolio anomaly scan...")
        
        results = {
            'scan_started_at': datetime.now().isoformat(),
            'client_id': client_id,
            'anomalies_detected': 0,
            'by_type': {},
            'by_severity': {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0},
            'leases_scanned': 0,
            'alerts_created': 0
        }
        
        # Get all active leases
        query = self.sb.table("leases").select("*")
        if client_id:
            query = query.eq("uploaded_by", client_id)
        query = query.neq("status", "DELETED")
        
        leases_response = query.execute()
        leases = leases_response.data if leases_response.data else []
        results['leases_scanned'] = len(leases)
        
        print(f"📊 Scanning {len(leases)} leases...")
        
        all_anomalies = []
        
        for lease in leases:
            lease_id = lease['id']
            
            # Run all anomaly checks
            anomalies = []
            anomalies.extend(self._check_critical_dates(lease))
            anomalies.extend(self._check_expired_lease(lease))
            anomalies.extend(self._check_confidence_scores(lease))
            anomalies.extend(self._check_missing_data(lease))
            anomalies.extend(self._check_rent_escalation(lease))
            anomalies.extend(self._check_cam_charge_trends(lease))
            anomalies.extend(self._check_asc842_compliance(lease))
            
            # Save anomalies to database
            for anomaly in anomalies:
                anomaly['lease_id'] = lease_id
                
                # Track by type
                anom_type = anomaly['anomaly_type']
                results['by_type'][anom_type] = results['by_type'].get(anom_type, 0) + 1
                
                # Track by severity
                severity = anomaly['severity']
                results['by_severity'][severity] += 1
                
                # Insert into database
                try:
                    self.sb.table("lease_anomalies").insert(anomaly).execute()
                    results['anomalies_detected'] += 1
                    all_anomalies.append(anomaly)
                except Exception as e:
                    print(f"❌ Error saving anomaly: {str(e)}")
        
        # Create alerts for high/critical anomalies
        high_priority = [a for a in all_anomalies if a['severity'] in ['CRITICAL', 'HIGH']]
        for anomaly in high_priority:
            self._create_alert(anomaly, client_id)
            results['alerts_created'] += 1
        
        results['scan_completed_at'] = datetime.now().isoformat()
        
        print(f"✅ Scan complete! Detected {results['anomalies_detected']} anomalies")
        print(f"   CRITICAL: {results['by_severity']['CRITICAL']}")
        print(f"   HIGH: {results['by_severity']['HIGH']}")
        print(f"   MEDIUM: {results['by_severity']['MEDIUM']}")
        print(f"   LOW: {results['by_severity']['LOW']}")
        
        return results
    
    def _check_critical_dates(self, lease: Dict) -> List[Dict]:
        """Check for upcoming critical date deadlines"""
        anomalies = []
        
        # Get extracted fields for this lease
        fields_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).execute()
        fields = {f['field_name']: f for f in (fields_response.data or [])}
        
        # Critical date fields to check
        critical_fields = [
            'Lease Expiration Date',
            'Renewal Option Deadline',
            'Renewal Notice Deadline',
            'Termination Notice Deadline',
            'Purchase Option Deadline'
        ]
        
        today = datetime.now().date()
        
        for field_name in critical_fields:
            if field_name in fields:
                field_data = fields[field_name]
                date_str = field_data.get('reviewed_value') or field_data.get('raw_value')
                
                if date_str and date_str != 'NOT FOUND':
                    try:
                        # Parse date (handle various formats)
                        deadline_date = self._parse_date(date_str)
                        if deadline_date:
                            days_until = (deadline_date - today).days
                            
                            # Only flag if in the future and within 90 days
                            if 0 < days_until <= 90:
                                severity = self._get_date_severity(days_until)
                                
                                anomalies.append({
                                    'anomaly_type': 'CRITICAL_DATE_APPROACHING',
                                    'severity': severity,
                                    'title': f'{field_name} in {days_until} days',
                                    'description': f'{field_name} is approaching on {deadline_date.strftime("%B %d, %Y")}. Immediate action may be required.',
                                    'field_name': field_name,
                                    'reference_date': deadline_date.isoformat(),
                                    'days_until_deadline': days_until,
                                    'expected_value': None,
                                    'actual_value': date_str
                                })
                    except:
                        pass
        
        return anomalies
    
    def _check_expired_lease(self, lease: Dict) -> List[Dict]:
        """Check if lease is expired but still marked active"""
        anomalies = []
        
        if lease.get('status') not in ['ACTIVE', 'PENDING_RENEWAL']:
            return anomalies
        
        # Get expiration date
        fields_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).eq("field_name", "Lease Expiration Date").execute()
        
        if fields_response.data:
            field_data = fields_response.data[0]
            date_str = field_data.get('reviewed_value') or field_data.get('raw_value')
            
            if date_str and date_str != 'NOT FOUND':
                try:
                    expiration_date = self._parse_date(date_str)
                    if expiration_date:
                        today = datetime.now().date()
                        days_expired = (today - expiration_date).days
                        
                        if days_expired > 0:
                            anomalies.append({
                                'anomaly_type': 'EXPIRED_LEASE_ACTIVE',
                                'severity': 'HIGH' if days_expired > 30 else 'MEDIUM',
                                'title': f'Lease expired {days_expired} days ago',
                                'description': f'This lease expired on {expiration_date.strftime("%B %d, %Y")} but is still marked as {lease.get("status")}. Update lease status or verify renewal.',
                                'field_name': 'Lease Expiration Date',
                                'reference_date': expiration_date.isoformat(),
                                'expected_value': 'EXPIRED or RENEWED',
                                'actual_value': lease.get('status')
                            })
                except:
                    pass
        
        return anomalies
    
    def _check_confidence_scores(self, lease: Dict) -> List[Dict]:
        """Check for fields with low confidence scores"""
        anomalies = []
        
        # Get all extracted fields
        fields_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).execute()
        fields = fields_response.data or []
        
        # Count low confidence fields
        low_confidence = [f for f in fields if f.get('confidence') == 'LOW']
        not_found = [f for f in fields if (f.get('reviewed_value') or f.get('raw_value', '')).upper() == 'NOT FOUND']
        
        total_issues = len(low_confidence) + len(not_found)
        
        if total_issues > 0:
            severity = self._get_confidence_severity(total_issues)
            
            issue_fields = [f['field_name'] for f in (low_confidence + not_found)[:5]]  # First 5
            
            anomalies.append({
                'anomaly_type': 'LOW_CONFIDENCE_FIELDS',
                'severity': severity,
                'title': f'{total_issues} fields need review',
                'description': f'This lease has {total_issues} fields with low confidence or missing data: {", ".join(issue_fields)}{"..." if total_issues > 5 else ""}. Manual review recommended.',
                'field_name': None,
                'expected_value': None,
                'actual_value': f'{total_issues} fields'
            })
        
        return anomalies
    
    def _check_missing_data(self, lease: Dict) -> List[Dict]:
        """Check for critical missing data"""
        anomalies = []
        
        # Critical fields that should always be present
        critical_fields = [
            'Tenant Legal Name',
            'Lease Commencement Date',
            'Lease Expiration Date',
            'Base Rent Year 1 (monthly)',
            'Premises Square Footage (RSF)'
        ]
        
        fields_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).execute()
        fields_dict = {f['field_name']: f for f in (fields_response.data or [])}
        
        missing = []
        for field_name in critical_fields:
            if field_name not in fields_dict:
                missing.append(field_name)
            else:
                value = fields_dict[field_name].get('reviewed_value') or fields_dict[field_name].get('raw_value', '')
                if not value or value.upper() in ['NOT FOUND', 'N/A', 'NONE']:
                    missing.append(field_name)
        
        if missing:
            anomalies.append({
                'anomaly_type': 'MISSING_DATA',
                'severity': 'HIGH' if len(missing) >= 3 else 'MEDIUM',
                'title': f'{len(missing)} critical fields missing',
                'description': f'Missing critical data: {", ".join(missing)}. Complete lease abstraction required.',
                'field_name': None,
                'expected_value': 'Complete data',
                'actual_value': f'{len(missing)} missing'
            })
        
        return anomalies
    
    def _check_rent_escalation(self, lease: Dict) -> List[Dict]:
        """Check rent escalation expectations vs. reality"""
        anomalies = []
        
        # Get rent and escalation info
        fields_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).execute()
        fields_dict = {f['field_name']: f for f in (fields_response.data or [])}
        
        # Get base rent year 1
        base_rent_field = fields_dict.get('Base Rent Year 1 (monthly)', {})
        base_rent_str = base_rent_field.get('reviewed_value') or base_rent_field.get('raw_value', '')
        
        # Get escalation
        escalation_field = fields_dict.get('Annual Escalation Rate or Cap', {})
        escalation_str = escalation_field.get('reviewed_value') or escalation_field.get('raw_value', '')
        
        if base_rent_str and escalation_str:
            try:
                # Parse base rent
                base_rent = float(''.join(c for c in base_rent_str if c.isdigit() or c == '.'))
                
                # Parse escalation rate
                escalation_rate = 0
                if '%' in escalation_str:
                    escalation_rate = float(''.join(c for c in escalation_str.replace('%', '') if c.isdigit() or c == '.')) / 100
                
                # Calculate expected rent in current year (simplified - would need lease start date for accuracy)
                # For now, just flag if escalation seems unusual
                if escalation_rate > 0.10:  # More than 10% escalation
                    anomalies.append({
                        'anomaly_type': 'RENT_ESCALATION_MISMATCH',
                        'severity': 'MEDIUM',
                        'title': f'Unusually high rent escalation: {escalation_rate*100:.1f}%',
                        'description': f'Annual rent escalation of {escalation_rate*100:.1f}% appears high. Verify escalation terms are correct.',
                        'field_name': 'Annual Escalation Rate or Cap',
                        'expected_value': '2-5% typical',
                        'actual_value': f'{escalation_rate*100:.1f}%'
                    })
            except:
                pass
        
        return anomalies
    
    def _get_date_severity(self, days_until: int) -> str:
        """Determine severity based on days until deadline"""
        thresholds = self.SEVERITY_THRESHOLDS['CRITICAL_DATE']
        if days_until <= thresholds['CRITICAL']:
            return 'CRITICAL'
        elif days_until <= thresholds['HIGH']:
            return 'HIGH'
        elif days_until <= thresholds['MEDIUM']:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _get_confidence_severity(self, count: int) -> str:
        """Determine severity based on number of low confidence fields"""
        thresholds = self.SEVERITY_THRESHOLDS['CONFIDENCE']
        if count >= thresholds['CRITICAL']:
            return 'CRITICAL'
        elif count >= thresholds['HIGH']:
            return 'HIGH'
        elif count >= thresholds['MEDIUM']:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str or date_str.upper() in ['NOT FOUND', 'N/A', 'NONE']:
            return None
        
        # Try common date formats
        formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y', '%b %d, %Y', '%Y/%m/%d']
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except:
                continue
        
        return None
    
    def _create_alert(self, anomaly: Dict, client_id: str):
        """Create a portfolio alert from an anomaly"""
        try:
            alert_data = {
                'client_id': client_id,
                'lease_id': anomaly.get('lease_id'),
                'alert_type': 'ANOMALY_DETECTED',
                'severity': anomaly['severity'],
                'priority': 1 if anomaly['severity'] == 'CRITICAL' else 2 if anomaly['severity'] == 'HIGH' else 3,
                'title': anomaly['title'],
                'message': anomaly['description'],
                'action_url': f'/Lease_Review?lease_id={anomaly.get("lease_id")}',
                'action_label': 'Review Lease',
                'status': 'ACTIVE'
            }
            
            self.sb.table("portfolio_alerts").insert(alert_data).execute()
            
            # Mark anomaly as alerted
            if 'id' in anomaly:
                self.sb.table("lease_anomalies").update({
                    'alert_sent': True,
                    'alert_sent_at': datetime.now().isoformat()
                }).eq('id', anomaly['id']).execute()
        
        except Exception as e:
            print(f"❌ Error creating alert: {str(e)}")
    
    def get_active_anomalies(self, client_id: str = None, severity: str = None) -> List[Dict]:
        """Get all active anomalies for a client"""
        query = self.sb.table("lease_anomalies").select("*, leases(property_address, tenant_name)").eq("status", "OPEN")
        
        if client_id:
            # Filter by client via lease relationship
            query = query.eq("leases.uploaded_by", client_id)
        
        if severity:
            query = query.eq("severity", severity)
        
        query = query.order("detected_at", desc=True)
        
        response = query.execute()
        return response.data if response.data else []
    
    def resolve_anomaly(self, anomaly_id: str, resolution_notes: str, resolved_by: str):
        """Mark an anomaly as resolved"""
        update_data = {
            'status': 'RESOLVED',
            'resolution_notes': resolution_notes,
            'resolved_at': datetime.now().isoformat(),
            'resolved_by': resolved_by
        }
        
        self.sb.table("lease_anomalies").update(update_data).eq("id", anomaly_id).execute()
        print(f"✅ Anomaly {anomaly_id} marked as resolved")
    
    def _check_cam_charge_trends(self, lease: Dict) -> List[Dict]:
        """
        Check for unusual CAM charge trends (year-over-year)
        Phase 6 Session 2 Enhancement
        """
        anomalies = []
        
        try:
            # Get CAM reconciliations for this lease
            recons_response = self.sb.table("cam_reconciliations").select("*").eq("lease_id", lease['id']).order("reconciliation_date", desc=True).limit(2).execute()
            
            recons = recons_response.data if recons_response.data else []
            
            if len(recons) < 2:
                # Need at least 2 years of data to detect trends
                return anomalies
            
            # Get most recent and previous year
            current = recons[0]
            previous = recons[1]
            
            # Calculate year-over-year variance
            current_total = float(current.get('landlord_billed_amount', 0) or 0)
            previous_total = float(previous.get('landlord_billed_amount', 0) or 0)
            
            if previous_total > 0:
                variance_pct = ((current_total - previous_total) / previous_total) * 100
                variance_amount = current_total - previous_total
                
                # Flag if CAM charges increased by more than 15% YoY
                if variance_pct > 15:
                    anomalies.append({
                        'anomaly_type': 'CAM_CHARGE_SPIKE',
                        'severity': 'HIGH' if variance_pct > 25 else 'MEDIUM',
                        'title': f'CAM charges increased {variance_pct:.1f}% year-over-year',
                        'description': f'CAM charges rose from ${previous_total:,.2f} to ${current_total:,.2f} (${variance_amount:,.2f} increase). This {variance_pct:.1f}% increase exceeds typical market trends and should be audited.',
                        'field_name': 'CAM Reconciliation',
                        'expected_value': f'< 15% increase (${previous_total * 1.15:,.2f})',
                        'actual_value': f'{variance_pct:.1f}% increase (${current_total:,.2f})'
                    })
                
                # Flag if CAM charges decreased significantly (possible under-billing or error)
                elif variance_pct < -15:
                    anomalies.append({
                        'anomaly_type': 'CAM_CHARGE_DROP',
                        'severity': 'MEDIUM',
                        'title': f'CAM charges decreased {abs(variance_pct):.1f}% year-over-year',
                        'description': f'CAM charges dropped from ${previous_total:,.2f} to ${current_total:,.2f}. Verify this is correct and not a billing error.',
                        'field_name': 'CAM Reconciliation',
                        'expected_value': f'Within 15% of ${previous_total:,.2f}',
                        'actual_value': f'{variance_pct:.1f}% decrease (${current_total:,.2f})'
                    })
        
        except Exception as e:
            # Silently skip if error - don't fail entire scan
            pass
        
        return anomalies
    
    def _check_asc842_compliance(self, lease: Dict) -> List[Dict]:
        """
        Check for ASC 842 compliance gaps
        Phase 6 Session 2 Enhancement
        """
        anomalies = []
        
        # ASC 842 requires specific fields to be captured
        required_fields_asc842 = [
            'Lease Commencement Date',
            'Lease Expiration Date',
            'Base Rent Year 1 (monthly)',
            'Premises Square Footage (RSF)',
            'Annual Escalation Rate or Cap',
            'Tenant Improvement Allowance',
            'Security Deposit Amount'
        ]
        
        # Get extracted fields for this lease
        fields_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).execute()
        fields_dict = {f['field_name']: f for f in (fields_response.data or [])}
        
        missing_asc842 = []
        low_confidence_asc842 = []
        
        for field_name in required_fields_asc842:
            if field_name not in fields_dict:
                missing_asc842.append(field_name)
            else:
                field_data = fields_dict[field_name]
                value = field_data.get('reviewed_value') or field_data.get('raw_value', '')
                confidence = field_data.get('confidence', 'LOW')
                
                # Check if value is missing or marked as NOT FOUND
                if not value or value.upper() in ['NOT FOUND', 'N/A', 'NONE', '']:
                    missing_asc842.append(field_name)
                # Check if confidence is low
                elif confidence == 'LOW':
                    low_confidence_asc842.append(field_name)
        
        # Flag if critical ASC 842 fields are missing
        if len(missing_asc842) >= 3:
            anomalies.append({
                'anomaly_type': 'ASC842_COMPLIANCE_GAP',
                'severity': 'HIGH',
                'title': f'ASC 842 compliance gap: {len(missing_asc842)} required fields missing',
                'description': f'This lease is missing critical ASC 842 required fields: {", ".join(missing_asc842[:5])}{"..." if len(missing_asc842) > 5 else ""}. Complete abstraction required for GAAP compliance.',
                'field_name': None,
                'expected_value': 'All ASC 842 required fields present',
                'actual_value': f'{len(missing_asc842)} fields missing'
            })
        
        # Flag if multiple ASC 842 fields have low confidence
        if len(low_confidence_asc842) >= 3:
            anomalies.append({
                'anomaly_type': 'ASC842_LOW_CONFIDENCE',
                'severity': 'MEDIUM',
                'title': f'ASC 842 fields need verification: {len(low_confidence_asc842)} low confidence fields',
                'description': f'ASC 842 required fields with low confidence: {", ".join(low_confidence_asc842[:5])}. Manual review recommended for audit readiness.',
                'field_name': None,
                'expected_value': 'High confidence on ASC 842 fields',
                'actual_value': f'{len(low_confidence_asc842)} low confidence fields'
            })
        
        # Check for missing discount rate (required for ROU asset calculation)
        if 'Discount Rate' not in fields_dict or not fields_dict.get('Discount Rate', {}).get('reviewed_value'):
            # Only flag if lease is active and relatively new (< 2 years old)
            if lease.get('status') in ['ACTIVE', 'PENDING_RENEWAL']:
                try:
                    commencement = fields_dict.get('Lease Commencement Date', {})
                    comm_date_str = commencement.get('reviewed_value') or commencement.get('raw_value')
                    if comm_date_str and comm_date_str != 'NOT FOUND':
                        comm_date = self._parse_date(comm_date_str)
                        if comm_date:
                            years_since_commencement = (datetime.now().date() - comm_date).days / 365.25
                            if years_since_commencement < 2:
                                anomalies.append({
                                    'anomaly_type': 'ASC842_MISSING_DISCOUNT_RATE',
                                    'severity': 'MEDIUM',
                                    'title': 'Missing discount rate for ROU asset calculation',
                                    'description': 'ASC 842 requires a discount rate (incremental borrowing rate) to calculate the Right-of-Use (ROU) asset. This field is missing.',
                                    'field_name': 'Discount Rate',
                                    'expected_value': 'Discount rate present',
                                    'actual_value': 'Missing'
                                })
                except:
                    pass
        
        return anomalies


# Convenience functions
def scan_portfolio_for_anomalies(supabase_client, client_id: str = None) -> Dict:
    """Scan portfolio and detect anomalies"""
    engine = AnomalyDetectionEngine(supabase_client)
    return engine.scan_portfolio(client_id)


def get_active_anomalies(supabase_client, client_id: str = None, severity: str = None) -> List[Dict]:
    """Get active anomalies"""
    engine = AnomalyDetectionEngine(supabase_client)
    return engine.get_active_anomalies(client_id, severity)


def resolve_anomaly(supabase_client, anomaly_id: str, notes: str, resolved_by: str):
    """Resolve an anomaly"""
    engine = AnomalyDetectionEngine(supabase_client)
    engine.resolve_anomaly(anomaly_id, notes, resolved_by)
