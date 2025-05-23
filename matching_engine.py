import json
import logging
from typing import List, Dict, Any
from models import Job, User, ServiceProviderProfile, JobMatch, Notification
from app import db
from ai_agents import SmartMatchingAgent

class JobMatchingEngine:
    """Smart job matching system that connects relevant service providers to job postings"""
    
    def __init__(self):
        self.ai_agent = SmartMatchingAgent()
        self.min_match_score = 0.3  # Minimum score to create a match
        self.notification_threshold = 0.5  # Minimum score to send notification
    
    def find_matches(self, job: Job) -> List[JobMatch]:
        """
        Find and create job matches for a given job posting
        
        Args:
            job: Job object to find matches for
            
        Returns:
            List of JobMatch objects
        """
        matches = []
        
        try:
            # Get eligible service providers
            eligible_providers = self._get_eligible_providers(job)
            
            logging.info(f"Found {len(eligible_providers)} eligible providers for job {job.id}")
            
            for provider in eligible_providers:
                try:
                    # Calculate match score using AI
                    match_result = self.ai_agent.calculate_match_score(job, provider.service_provider_profile)
                    match_score = match_result.get('match_score', 0.0)
                    
                    # Only create match if score meets minimum threshold
                    if match_score >= self.min_match_score:
                        match = JobMatch(
                            job_id=job.id,
                            service_provider_id=provider.id,
                            match_score=match_score,
                            match_reasons=json.dumps(match_result.get('reasons', [])),
                            is_notified=False
                        )
                        matches.append(match)
                        
                        # Create notification if score is high enough
                        if match_score >= self.notification_threshold:
                            self._create_match_notification(job, provider, match_score, match_result)
                        
                        logging.info(f"Created match: Job {job.id} -> Provider {provider.id} (Score: {match_score:.2f})")
                    
                except Exception as e:
                    logging.error(f"Failed to calculate match for provider {provider.id}: {str(e)}")
                    continue
            
            # Sort matches by score (highest first)
            matches.sort(key=lambda x: x.match_score, reverse=True)
            
            logging.info(f"Created {len(matches)} matches for job {job.id}")
            
        except Exception as e:
            logging.error(f"Job matching failed for job {job.id}: {str(e)}")
        
        return matches
    
    def _get_eligible_providers(self, job: Job) -> List[User]:
        """
        Get list of eligible service providers for a job
        
        Args:
            job: Job object
            
        Returns:
            List of User objects (service providers)
        """
        query = User.query.filter(
            User.role == 'service_provider',
            User.is_approved == True
        ).join(ServiceProviderProfile)
        
        # Filter by profession type if specified
        if job.profession_type and job.profession_type != 'both':
            query = query.filter(ServiceProviderProfile.profession == job.profession_type)
        
        # Filter by location proximity (basic string matching for now)
        if job.location:
            query = query.filter(
                ServiceProviderProfile.location.ilike(f'%{job.location}%')
            )
        
        # Filter by budget compatibility
        if job.budget_max:
            query = query.filter(
                db.or_(
                    ServiceProviderProfile.hourly_rate == None,
                    ServiceProviderProfile.hourly_rate <= job.budget_max * 1.2  # Allow 20% flexibility
                )
            )
        
        return query.all()
    
    def _create_match_notification(self, job: Job, provider: User, match_score: float, match_result: Dict[str, Any]):
        """
        Create notification for a job match
        
        Args:
            job: Job object
            provider: Service provider User object
            match_score: Match score
            match_result: Full match analysis result
        """
        try:
            reasons = match_result.get('reasons', [])
            reasons_text = ', '.join(reasons[:3])  # Show top 3 reasons
            
            notification = Notification(
                user_id=provider.id,
                title=f'New Job Match: {job.title}',
                message=f'We found a {match_score:.0%} match for you! Reasons: {reasons_text}. '
                       f'Budget: ${job.budget_min}-${job.budget_max} | Location: {job.location}',
                type='job_match',
                related_job_id=job.id
            )
            
            db.session.add(notification)
            logging.info(f"Created notification for provider {provider.id} for job {job.id}")
            
        except Exception as e:
            logging.error(f"Failed to create notification: {str(e)}")
    
    def update_provider_matches(self, provider_id: int):
        """
        Update matches for a service provider when their profile changes
        
        Args:
            provider_id: Service provider user ID
        """
        try:
            # Get recent open jobs
            recent_jobs = Job.query.filter(
                Job.status == 'open',
                Job.created_at >= db.func.date_sub(db.func.current_date(), db.text('INTERVAL 30 DAY'))
            ).all()
            
            provider = User.query.get(provider_id)
            if not provider or not provider.service_provider_profile:
                return
            
            for job in recent_jobs:
                # Check if match already exists
                existing_match = JobMatch.query.filter_by(
                    job_id=job.id,
                    service_provider_id=provider_id
                ).first()
                
                if not existing_match:
                    # Calculate new match
                    match_result = self.ai_agent.calculate_match_score(job, provider.service_provider_profile)
                    match_score = match_result.get('match_score', 0.0)
                    
                    if match_score >= self.min_match_score:
                        match = JobMatch(
                            job_id=job.id,
                            service_provider_id=provider_id,
                            match_score=match_score,
                            match_reasons=json.dumps(match_result.get('reasons', []))
                        )
                        db.session.add(match)
                        
                        if match_score >= self.notification_threshold:
                            self._create_match_notification(job, provider, match_score, match_result)
            
            db.session.commit()
            logging.info(f"Updated matches for provider {provider_id}")
            
        except Exception as e:
            logging.error(f"Failed to update matches for provider {provider_id}: {str(e)}")
    
    def get_match_statistics(self, job_id: int) -> Dict[str, Any]:
        """
        Get matching statistics for a job
        
        Args:
            job_id: Job ID
            
        Returns:
            Dict with match statistics
        """
        try:
            matches = JobMatch.query.filter_by(job_id=job_id).all()
            
            if not matches:
                return {
                    'total_matches': 0,
                    'avg_score': 0.0,
                    'score_distribution': {},
                    'top_reasons': []
                }
            
            scores = [m.match_score for m in matches]
            avg_score = sum(scores) / len(scores)
            
            # Score distribution
            score_ranges = {
                'excellent': len([s for s in scores if s >= 0.8]),
                'good': len([s for s in scores if 0.6 <= s < 0.8]),
                'fair': len([s for s in scores if 0.4 <= s < 0.6]),
                'poor': len([s for s in scores if s < 0.4])
            }
            
            # Aggregate reasons
            all_reasons = []
            for match in matches:
                if match.match_reasons:
                    reasons = json.loads(match.match_reasons)
                    all_reasons.extend(reasons)
            
            # Count reason frequency
            reason_counts = {}
            for reason in all_reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
            
            top_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            
            return {
                'total_matches': len(matches),
                'avg_score': avg_score,
                'score_distribution': score_ranges,
                'top_reasons': [{'reason': r[0], 'count': r[1]} for r in top_reasons]
            }
            
        except Exception as e:
            logging.error(f"Failed to get match statistics for job {job_id}: {str(e)}")
            return {
                'total_matches': 0,
                'avg_score': 0.0,
                'score_distribution': {},
                'top_reasons': [],
                'error': str(e)
            }
    
    def rematch_job(self, job_id: int) -> List[JobMatch]:
        """
        Re-run matching for a job (useful when job details are updated)
        
        Args:
            job_id: Job ID to rematch
            
        Returns:
            List of new JobMatch objects
        """
        try:
            job = Job.query.get(job_id)
            if not job:
                return []
            
            # Delete existing matches
            JobMatch.query.filter_by(job_id=job_id).delete()
            db.session.commit()
            
            # Create new matches
            new_matches = self.find_matches(job)
            
            for match in new_matches:
                db.session.add(match)
            
            db.session.commit()
            logging.info(f"Rematched job {job_id}, created {len(new_matches)} new matches")
            
            return new_matches
            
        except Exception as e:
            logging.error(f"Failed to rematch job {job_id}: {str(e)}")
            return []
