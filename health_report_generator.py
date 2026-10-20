"""
LeaseAI - Portfolio Health Report Generator
Phase 6: Agentic AI Layer

Generates weekly portfolio health reports with:
- GPT-4o executive summary
- Portfolio metrics and insights
- Critical dates summary
- Anomaly highlights
- Prioritized action items
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import openai


class PortfolioHealthReportGenerator:
    """
    Generates comprehensive portfolio health reports
    """
    
    def __init__(self, supabase_client, openai_api_key: str):
        """Initialize health report generator"""
        self.sb = supabase_client
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
    
    def generate_report(self, client_id: str, report_date: datetime = None) -> Dict:
        """
        Generate a comprehensive portfolio health report
        
        Args:
            client_id: UUID of the client
            report_date: Date of the report (defaults to today)
            
        Returns:
            Dictionary with report data and ID
        """
        if not report_date:
            report_date = datetime.now().date()
        
        print(f"📊 Generating health report for {report_date}...")
        
        # Step 1: Gather portfolio metrics
        metrics = self._gather_portfolio_metrics(client_id)
        print(f"✓ Gathered portfolio metrics")
        
        # Step 2: Get critical dates summary
        critical_dates = self._get_critical_dates_summary(client_id)
        print(f"✓ Analyzed critical dates")
        
        # Step 3: Get anomalies summary
        anomalies = self._get_anomalies_summary(client_id)
        print(f"✓ Summarized anomalies")
        
        # Step 4: Generate recommended actions
        actions = self._generate_recommended_actions(metrics, critical_dates, anomalies)
        print(f"✓ Generated {len(actions)} recommended actions")
        
        # Step 5: Calculate health score
        health_score, health_status = self._calculate_health_score(metrics, anomalies)
        print(f"✓ Calculated health score: {health_score}/100 ({health_status})")
        
        # Step 6: Generate AI executive summary
        executive_summary = self._generate_executive_summary(
            metrics, critical_dates, anomalies, actions, health_score
        )
        print(f"✓ Generated AI executive summary")
        
        # Step 7: Save report to database
        report_data = {
            'client_id': client_id,
            'report_date': report_date.isoformat(),
            'report_week': report_date.isocalendar()[1],
            'report_year': report_date.year,
            'executive_summary': executive_summary,
            'total_leases': metrics['total_leases'],
            'active_leases': metrics['active_leases'],
            'expiring_soon': metrics['expiring_soon'],
            'requires_attention': metrics['requires_attention'],
            'total_monthly_rent': float(metrics['total_monthly_rent']),
            'avg_rent_per_sqft': float(metrics['avg_rent_per_sqft']),
            'total_portfolio_sqft': metrics['total_portfolio_sqft'],
            'critical_dates_30_days': critical_dates['next_30_days'],
            'critical_dates_60_days': critical_dates['next_60_days'],
            'critical_dates_90_days': critical_dates['next_90_days'],
            'anomalies_detected': anomalies['total'],
            'high_severity_anomalies': anomalies['high_severity'],
            'recommended_actions': json.dumps(actions),
            'health_score': health_score,
            'health_status': health_status,
            'status': 'GENERATED'
        }
        
        response = self.sb.table("portfolio_health_reports").insert(report_data).execute()
        report_id = response.data[0]['id'] if response.data else None
        
        # Step 8: Save action items
        if report_id and actions:
            self._save_action_items(report_id, actions)
        
        print(f"✅ Health report generated! ID: {report_id}")
        
        return {
            'report_id': report_id,
            'report_data': report_data,
            'metrics': metrics,
            'critical_dates': critical_dates,
            'anomalies': anomalies,
            'actions': actions
        }
    
    def _gather_portfolio_metrics(self, client_id: str) -> Dict:
        """Gather portfolio-wide metrics"""
        
        # Get all leases
        leases_response = self.sb.table("leases").select("*").eq("uploaded_by", client_id).execute()
        all_leases = leases_response.data if leases_response.data else []
        
        # Count active leases
        active_leases = [l for l in all_leases if l.get('status') in ['ACTIVE', 'PENDING_RENEWAL']]
        
        # Get fields for financial metrics
        total_rent = 0
        total_sqft = 0
        leases_with_rent = 0
        leases_with_sqft = 0
        
        for lease in active_leases:
            # Get monthly rent
            rent_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).eq("field_name", "Base Rent Year 1 (monthly)").execute()
            if rent_response.data:
                rent_str = rent_response.data[0].get('reviewed_value') or rent_response.data[0].get('raw_value', '')
                try:
                    rent = float(''.join(c for c in rent_str if c.isdigit() or c == '.'))
                    total_rent += rent
                    leases_with_rent += 1
                except:
                    pass
            
            # Get square footage
            sqft_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).eq("field_name", "Premises Square Footage (RSF)").execute()
            if sqft_response.data:
                sqft_str = sqft_response.data[0].get('reviewed_value') or sqft_response.data[0].get('raw_value', '')
                try:
                    sqft = int(''.join(c for c in sqft_str if c.isdigit()))
                    total_sqft += sqft
                    leases_with_sqft += 1
                except:
                    pass
        
        # Count expiring soon (next 90 days)
        expiring_soon = self._count_expiring_leases(active_leases, 90)
        
        # Count leases requiring attention (anomalies)
        anomalies_response = self.sb.table("lease_anomalies").select("lease_id").eq("status", "OPEN").execute()
        unique_leases_with_issues = len(set([a['lease_id'] for a in (anomalies_response.data or [])]))
        
        # Calculate averages
        avg_rent_per_sqft = (total_rent / total_sqft) if total_sqft > 0 else 0
        
        return {
            'total_leases': len(all_leases),
            'active_leases': len(active_leases),
            'expiring_soon': expiring_soon,
            'requires_attention': unique_leases_with_issues,
            'total_monthly_rent': total_rent,
            'avg_rent_per_sqft': avg_rent_per_sqft,
            'total_portfolio_sqft': total_sqft,
            'leases_with_complete_data': leases_with_rent
        }
    
    def _get_critical_dates_summary(self, client_id: str) -> Dict:
        """Summarize upcoming critical dates"""
        
        # Get all active leases for client
        leases_response = self.sb.table("leases").select("id").eq("uploaded_by", client_id).neq("status", "DELETED").execute()
        lease_ids = [l['id'] for l in (leases_response.data or [])]
        
        if not lease_ids:
            return {'next_30_days': 0, 'next_60_days': 0, 'next_90_days': 0, 'details': []}
        
        # Get critical date fields
        critical_fields = ['Lease Expiration Date', 'Renewal Option Deadline', 'Renewal Notice Deadline', 'Termination Notice Deadline']
        
        dates_30 = 0
        dates_60 = 0
        dates_90 = 0
        date_details = []
        
        today = datetime.now().date()
        
        for lease_id in lease_ids:
            fields_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease_id).in_("field_name", critical_fields).execute()
            
            for field in (fields_response.data or []):
                date_str = field.get('reviewed_value') or field.get('raw_value')
                if date_str and date_str != 'NOT FOUND':
                    try:
                        date_obj = self._parse_date(date_str)
                        if date_obj:
                            days_until = (date_obj - today).days
                            
                            if 0 < days_until <= 30:
                                dates_30 += 1
                                date_details.append({'field': field['field_name'], 'date': date_str, 'days': days_until})
                            if 0 < days_until <= 60:
                                dates_60 += 1
                            if 0 < days_until <= 90:
                                dates_90 += 1
                    except:
                        pass
        
        return {
            'next_30_days': dates_30,
            'next_60_days': dates_60,
            'next_90_days': dates_90,
            'details': sorted(date_details, key=lambda x: x['days'])[:5]  # Top 5 most urgent
        }
    
    def _get_anomalies_summary(self, client_id: str) -> Dict:
        """Summarize detected anomalies"""
        
        # Get leases for client
        leases_response = self.sb.table("leases").select("id").eq("uploaded_by", client_id).execute()
        lease_ids = [l['id'] for l in (leases_response.data or [])]
        
        if not lease_ids:
            return {'total': 0, 'high_severity': 0, 'by_type': {}, 'top_issues': []}
        
        # Get active anomalies
        anomalies_response = self.sb.table("lease_anomalies").select("*").in_("lease_id", lease_ids).eq("status", "OPEN").execute()
        anomalies = anomalies_response.data or []
        
        # Count by severity
        high_severity = len([a for a in anomalies if a['severity'] in ['CRITICAL', 'HIGH']])
        
        # Count by type
        by_type = {}
        for anom in anomalies:
            atype = anom['anomaly_type']
            by_type[atype] = by_type.get(atype, 0) + 1
        
        # Get top 5 most critical
        top_issues = sorted(
            [{'title': a['title'], 'severity': a['severity'], 'type': a['anomaly_type']} for a in anomalies],
            key=lambda x: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].index(x['severity'])
        )[:5]
        
        return {
            'total': len(anomalies),
            'high_severity': high_severity,
            'by_type': by_type,
            'top_issues': top_issues
        }
    
    def _generate_recommended_actions(self, metrics: Dict, critical_dates: Dict, anomalies: Dict) -> List[Dict]:
        """Generate prioritized recommended actions"""
        
        actions = []
        
        # Action 1: Address high-severity anomalies
        if anomalies['high_severity'] > 0:
            actions.append({
                'action_type': 'REVIEW_ANOMALIES',
                'priority': 1,
                'title': f'Review {anomalies["high_severity"]} high-priority anomalies',
                'description': 'Critical and high-severity issues detected across portfolio requiring immediate attention.'
            })
        
        # Action 2: Upcoming critical dates
        if critical_dates['next_30_days'] > 0:
            top_dates = critical_dates['details'][:3]
            date_list = ', '.join([f"{d['field']} ({d['days']} days)" for d in top_dates])
            actions.append({
                'action_type': 'REVIEW_CRITICAL_DATES',
                'priority': 1,
                'title': f'Urgent: {critical_dates["next_30_days"]} deadlines in next 30 days',
                'description': f'Action required: {date_list}'
            })
        
        # Action 3: Leases requiring attention
        if metrics['requires_attention'] > 0:
            actions.append({
                'action_type': 'REVIEW_LEASES',
                'priority': 2,
                'title': f'Review {metrics["requires_attention"]} leases with issues',
                'description': 'Leases with low confidence fields, missing data, or detected anomalies.'
            })
        
        # Action 4: Expiring leases
        if metrics['expiring_soon'] > 0:
            actions.append({
                'action_type': 'PLAN_RENEWALS',
                'priority': 2,
                'title': f'Plan for {metrics["expiring_soon"]} leases expiring in 90 days',
                'description': 'Review renewal options and begin negotiations with landlords.'
            })
        
        # Action 5: Complete portfolio review
        completion_rate = (metrics['leases_with_complete_data'] / max(metrics['active_leases'], 1)) * 100
        if completion_rate < 80:
            actions.append({
                'action_type': 'COMPLETE_ABSTRACTIONS',
                'priority': 3,
                'title': f'Complete lease abstractions ({completion_rate:.0f}% complete)',
                'description': 'Some leases have incomplete data. Run extraction on remaining leases.'
            })
        
        return actions
    
    def _calculate_health_score(self, metrics: Dict, anomalies: Dict) -> tuple:
        """Calculate portfolio health score (0-100)"""
        
        score = 100
        
        # Deduct for anomalies
        score -= anomalies['total'] * 2  # 2 points per anomaly
        score -= anomalies['high_severity'] * 5  # Extra 5 points for high severity
        
        # Deduct for incomplete data
        if metrics['active_leases'] > 0:
            completion_rate = (metrics['leases_with_complete_data'] / metrics['active_leases'])
            score -= (1 - completion_rate) * 20  # Up to 20 points for incomplete data
        
        # Deduct for leases requiring attention
        attention_rate = (metrics['requires_attention'] / max(metrics['active_leases'], 1))
        score -= attention_rate * 15  # Up to 15 points
        
        # Ensure score is 0-100
        score = max(0, min(100, int(score)))
        
        # Determine status
        if score >= 90:
            status = 'EXCELLENT'
        elif score >= 75:
            status = 'GOOD'
        elif score >= 50:
            status = 'NEEDS_ATTENTION'
        else:
            status = 'CRITICAL'
        
        return score, status
    
    def _generate_executive_summary(self, metrics: Dict, critical_dates: Dict, anomalies: Dict, actions: List[Dict], health_score: int) -> str:
        """Generate AI-powered executive summary using GPT-4o"""
        
        prompt = f"""You are a commercial real estate portfolio analyst. Write a concise 3-4 sentence executive summary for this week's portfolio health report.

Portfolio Metrics:
- Total Active Leases: {metrics['active_leases']}
- Total Monthly Rent: ${metrics['total_monthly_rent']:,.2f}
- Average Rent per SF: ${metrics['avg_rent_per_sqft']:.2f}
- Total Portfolio SF: {metrics['total_portfolio_sqft']:,}
- Leases Expiring Soon (90 days): {metrics['expiring_soon']}
- Leases Requiring Attention: {metrics['requires_attention']}

Critical Dates:
- Deadlines in next 30 days: {critical_dates['next_30_days']}
- Deadlines in next 60 days: {critical_dates['next_60_days']}
- Deadlines in next 90 days: {critical_dates['next_90_days']}

Anomalies Detected:
- Total Anomalies: {anomalies['total']}
- High Severity: {anomalies['high_severity']}

Health Score: {health_score}/100

Top Priority Actions:
{chr(10).join([f"- {a['title']}" for a in actions[:3]])}

Write a professional, concise summary highlighting the most important points. Be specific with numbers. Start with overall portfolio health, then highlight urgent issues if any, then provide outlook."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Using mini for cost efficiency
                messages=[
                    {"role": "system", "content": "You are a commercial real estate portfolio analyst writing executive summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
        
        except Exception as e:
            print(f"⚠️ Error generating AI summary: {str(e)}")
            # Fallback to template
            return f"Your portfolio of {metrics['active_leases']} active leases is currently {health_score}/100. {anomalies['high_severity']} high-priority issues detected requiring immediate attention. {critical_dates['next_30_days']} critical deadlines in the next 30 days."
    
    def _save_action_items(self, report_id: str, actions: List[Dict]):
        """Save recommended actions to database"""
        
        for action in actions:
            action_data = {
                'health_report_id': report_id,
                'action_type': action['action_type'],
                'priority': action['priority'],
                'title': action['title'],
                'description': action['description'],
                'status': 'PENDING'
            }
            
            try:
                self.sb.table("health_report_actions").insert(action_data).execute()
            except Exception as e:
                print(f"⚠️ Error saving action: {str(e)}")
    
    def _count_expiring_leases(self, leases: List[Dict], days: int) -> int:
        """Count leases expiring within specified days"""
        count = 0
        today = datetime.now().date()
        target_date = today + timedelta(days=days)
        
        for lease in leases:
            exp_response = self.sb.table("extracted_fields").select("*").eq("lease_id", lease['id']).eq("field_name", "Lease Expiration Date").execute()
            
            if exp_response.data:
                date_str = exp_response.data[0].get('reviewed_value') or exp_response.data[0].get('raw_value')
                if date_str and date_str != 'NOT FOUND':
                    try:
                        exp_date = self._parse_date(date_str)
                        if exp_date and today < exp_date <= target_date:
                            count += 1
                    except:
                        pass
        
        return count
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string"""
        if not date_str or date_str.upper() in ['NOT FOUND', 'N/A', 'NONE']:
            return None
        
        formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y', '%b %d, %Y', '%Y/%m/%d']
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except:
                continue
        
        return None


# Convenience function
def generate_health_report(supabase_client, openai_api_key: str, client_id: str) -> Dict:
    """Generate a portfolio health report"""
    generator = PortfolioHealthReportGenerator(supabase_client, openai_api_key)
    return generator.generate_report(client_id)
