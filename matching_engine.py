import json
import logging
from typing import List, Dict, Any
from models import Job, User, ServiceProviderProfile, JobMatch, Notification
from app import db
from ai_agents import SmartMatchingAgent
from models import UserRole 
from sqlalchemy import or_

class JobMatchingEngine:
    """Smart job matching system that connects relevant service providers to job postings"""

    def __init__(self):
        self.ai_agent = SmartMatchingAgent()
        self.min_match_score = 0.3  # Minimum score to create a match
        self.notification_threshold = 0.5  # Minimum score to send notification

    def find_matches(self, job: Job) -> List[JobMatch]:
        matches = []

        try:
            eligible_providers = self._get_eligible_providers(job)
            logging.info(f"Found {len(eligible_providers)} eligible providers for job {job.id}")

            for provider in eligible_providers:
                try:
                    match_result = self.ai_agent.calculate_match_score(job, provider.service_provider_profile)
                    match_score = match_result.get('match_score', 0.0)

                    logging.info(f"Match score for provider {provider.id}: {match_score}")

                    if match_score >= self.min_match_score:
                        match = JobMatch(
                            job_id=job.id,
                            service_provider_id=provider.id,
                            match_score=match_score,
                            match_reasons=json.dumps(match_result.get('reasons', [])),
                            is_notified=False
                        )
                        matches.append(match)

                        if match_score >= self.notification_threshold:
                            self._create_match_notification(job, provider, match_score, match_result)
                            match.is_notified = True
                            db.session.add(match)

                        logging.info(f"Created match: Job {job.id} -> Provider {provider.id} (Score: {match_score:.2f})")

                except Exception as e:
                    logging.error(f"Failed to calculate match for provider {provider.id}: {str(e)}")
                    continue

            matches.sort(key=lambda x: x.match_score, reverse=True)

            for match in matches:
                db.session.add(match)

            db.session.commit()
            logging.info(f"Created {len(matches)} matches for job {job.id}")

        except Exception as e:
            logging.error(f"Job matching failed for job {job.id}: {str(e)}")

        return matches

    def _get_eligible_providers(self, job: Job) -> List[User]:
        return User.query.filter(
            or_(User.role == UserRole.fundi, User.role == UserRole.proffesional),
            User.is_approved == True
        ).join(ServiceProviderProfile).all()

    def _create_match_notification(self, job: Job, provider: User, match_score: float, match_result: Dict[str, Any]):
        try:
            reasons = match_result.get('reasons', [])
            reasons_text = ', '.join(reasons[:3])

            notification = Notification(
                user_id=provider.id,
                title=f'New Job Match: {job.title}',
                message=f'We found a {match_score:.0%} match for you! Reasons: {reasons_text}. '
                        f'Budget: ${job.budget_min}-${job.budget_max} | Location: {job.location}',
                type='job_match',
                related_job_id=job.id
            )

            db.session.add(notification)
            db.session.commit()
            logging.info(f"Created notification for provider {provider.id} for job {job.id}")

        except Exception as e:
            logging.error(f"Failed to create notification: {str(e)}")

    def update_provider_matches(self, provider_id: int):
        try:
            recent_jobs = Job.query.filter(
                Job.status == 'open',
                Job.created_at >= db.func.date_sub(db.func.current_date(), db.text('INTERVAL 30 DAY'))
            ).all()

            provider = User.query.get(provider_id)
            if not provider or not provider.service_provider_profile:
                return

            for job in recent_jobs:
                existing_match = JobMatch.query.filter_by(
                    job_id=job.id,
                    service_provider_id=provider_id
                ).first()

                if not existing_match:
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
                            match.is_notified = True
                            db.session.add(match)

            db.session.commit()
            logging.info(f"Updated matches for provider {provider_id}")

        except Exception as e:
            logging.error(f"Failed to update matches for provider {provider_id}: {str(e)}")

    def get_match_statistics(self, job_id: int) -> Dict[str, Any]:
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

            score_ranges = {
                'excellent': len([s for s in scores if s >= 0.8]),
                'good': len([s for s in scores if 0.6 <= s < 0.8]),
                'fair': len([s for s in scores if 0.4 <= s < 0.6]),
                'poor': len([s for s in scores if s < 0.4])
            }

            all_reasons = []
            for match in matches:
                if match.match_reasons:
                    reasons = json.loads(match.match_reasons)
                    all_reasons.extend(reasons)

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
        try:
            job = Job.query.get(job_id)
            if not job:
                return []

            JobMatch.query.filter_by(job_id=job_id).delete()
            db.session.commit()

            new_matches = self.find_matches(job)

            for match in new_matches:
                db.session.add(match)

            db.session.commit()
            logging.info(f"Rematched job {job_id}, created {len(new_matches)} new matches")

            return new_matches

        except Exception as e:
            logging.error(f"Failed to rematch job {job_id}: {str(e)}")
            return []
