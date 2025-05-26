import os
import json
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from app import app, db
from models import User, ServiceProviderProfile, CustomerProfile, Job, JobApplication, JobMatch, UserRole,Document, Notification, Message, ServiceProviderConnection
from ai_agents import AIVerificationAgent, AutofillAgent
from matching_engine import JobMatchingEngine
from document_processor import DocumentProcessor
from sqlalchemy import or_

# Initialize AI agents
ai_verification = AIVerificationAgent()
autofill_agent = AutofillAgent()
matching_engine = JobMatchingEngine()
doc_processor = DocumentProcessor()

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'customer':
            return redirect(url_for('customer_dashboard'))
        elif current_user.role == 'service_provider':
            return redirect(url_for('service_provider_dashboard'))
        elif current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
    return render_template('index.html')

from models import UserRole

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role_input = request.form['role']  # 'customer', 'fundi', 'professional', 'admin'
        
        # Validate role
        role_input = request.form.get('role')
        try:
            role_enum = UserRole(role_input)
        except ValueError:
            print(f"[ERROR] Invalid role input: {role_input}")  # optional debug print
            flash('Invalid user role selected.', 'error')
            return render_template('register.html')

        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')

        # Create user
        user = User(username=username, email=email, role=role_enum)
        user.set_password(password)

        # Auto-approve customer and admin
        if role_enum in [UserRole.customer, UserRole.admin]:
            user.is_approved = True

        db.session.add(user)
        db.session.commit()

        # Create profile depending on role
        if role_enum == UserRole.customer:
            profile = CustomerProfile(user_id=user.id)
            db.session.add(profile)

        elif role_enum in [UserRole.fundi, UserRole.proffesional]:
            profession = request.form.get('profession', role_enum.value)
            profile = ServiceProviderProfile(user_id=user.id, profession=profession)
            db.session.add(profile)
            db.session.commit()

            # Document handling
            document_types = ['certificates', 'portfolio', 'id_document', 'resume']
            uploaded_documents = []

            for doc_type in document_types:
                if doc_type in request.files:
                    files = request.files.getlist(doc_type)
                    for file in files:
                        if file and file.filename:
                            try:
                                filename = secure_filename(file.filename)
                                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
                                filename = timestamp + filename

                                upload_dir = app.config.get('UPLOAD_FOLDER', 'uploads')
                                os.makedirs(upload_dir, exist_ok=True)
                                file_path = os.path.join(upload_dir, filename)
                                file.save(file_path)

                                extracted_text = doc_processor.extract_text(file_path)
                                ai_analysis = doc_processor.analyze_document(extracted_text, doc_type)

                                document = Document(
                                    service_provider_id=profile.id,
                                    filename=filename,
                                    original_filename=file.filename,
                                    file_path=file_path,
                                    document_type=doc_type,
                                    extracted_text=extracted_text,
                                    ai_analysis=json.dumps(ai_analysis)
                                )
                                db.session.add(document)
                                uploaded_documents.append(doc_type)

                            except Exception:
                                continue

            db.session.commit()

            if uploaded_documents:
                flash(f'Registration successful! Documents uploaded: {", ".join(uploaded_documents)}. Your application is being processed by our AI system.', 'success')
            else:
                flash('Registration successful! Your application is pending admin approval.', 'success')
        
        else:
            flash('Registration successful! You can now log in.', 'success')

        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Check approval status only for service providers (fundi and professional)
            if not user.is_approved and user.role in [UserRole.fundi, UserRole.proffesional]:
                flash('Your account is pending approval. Please wait for admin verification.', 'warning')
                return render_template('login.html')
            
            login_user(user)
            flash('Login successful!', 'success')
            
            # Redirect based on role
            if user.role == UserRole.customer:
                return redirect(url_for('customer_dashboard'))
            elif user.role in [UserRole.fundi, UserRole.proffesional]:
                return redirect(url_for('service_provider_dashboard'))
            elif user.role == UserRole.admin:
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/customer/dashboard')
@login_required
def customer_dashboard():
    if current_user.role != UserRole.customer:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    jobs = Job.query.filter_by(customer_id=current_user.id).order_by(Job.created_at.desc()).all()
    return render_template('customer_dashboard.html', jobs=jobs)

@app.route('/service-provider/dashboard')
@login_required
def service_provider_dashboard():
    if current_user.role not in [UserRole.fundi, UserRole.proffesional]:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    matches = JobMatch.query.filter_by(service_provider_id=current_user.id).order_by(JobMatch.match_score.desc()).limit(10).all()
    applications = JobApplication.query.filter_by(applicant_id=current_user.id).order_by(JobApplication.created_at.desc()).all()
    
    return render_template('service_provider_dashboard.html', matches=matches, applications=applications)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != UserRole.admin:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    pending_users = User.query.filter(User.role.in_([UserRole.fundi, UserRole.proffesional]), User.is_approved == False).all()
    return render_template('admin_dashboard.html', pending_users=pending_users)

from flask import abort
from functools import wraps

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != UserRole.admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.route('/admin/approve/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def approve_user(user_id):
    print(f"Approve route triggered for user {user_id}")
    if current_user.role != UserRole.admin:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    
    # Create notification
    notification = Notification(
        user_id=user.id,
        title='Application Approved',
        message='Your service provider application has been approved. You can now log in and start applying for jobs.',
        type='approval'
    )
    db.session.add(notification)
    db.session.commit()
    
    flash(f'User {user.username} has been approved', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject/<int:user_id>', methods=['GET', 'POST'])
@admin_required
@login_required
def reject_user(user_id):
    if current_user.role != UserRole.admin:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    
    # Create notification before potential deletion
    notification = Notification(
        user_id=user.id,
        title='Application Rejected',
        message='Your service provider application has been rejected. Please contact support for more information.',
        type='approval'
    )
    db.session.add(notification)
    db.session.commit()
    
    flash(f'User {user.username} has been rejected', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/ai-verify/<int:user_id>', methods=['GET', 'POST'])
@admin_required
@login_required
def ai_verify_user(user_id):
    if current_user.role != UserRole.admin:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(user_id)
    profile = user.service_provider_profile
    
    if not profile:
        flash('No service provider profile found', 'error')
        return redirect(url_for('admin_dashboard'))
    
    try:
        # Run AI verification
        verification_result = ai_verification.verify_application(user, profile)
        
        # Update profile with AI results
        profile.ai_verification_score = verification_result['score']
        profile.ai_verification_notes = json.dumps(verification_result['analysis'])
        profile.verification_status = 'verified' if verification_result['approved'] else 'rejected'
        
        if verification_result['approved']:
            user.is_approved = True
            message = 'AI verification successful. User approved automatically.'
            notification_msg = 'Your application has been verified and approved by our AI system.'
        else:
            message = 'AI verification failed. User remains pending for manual review.'
            notification_msg = 'Your application requires additional review. Please ensure all documents are valid and complete.'
        
        # Create notification
        notification = Notification(
            user_id=user.id,
            title='Application Verified',
            message=notification_msg,
            type='approval'
        )
        db.session.add(notification)
        db.session.commit()
        
        flash(message, 'success' if verification_result['approved'] else 'warning')
        
    except Exception as e:
        flash(f'AI verification failed: {str(e)}', 'error')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/job/post', methods=['GET', 'POST'])
@login_required
def post_job():
    try:
        if current_user.role != UserRole.customer:
            flash('Only customers can post jobs', 'error')
            return redirect(url_for('index'))

        if request.method == 'POST':
            job = Job(
                customer_id=current_user.id,
                title=request.form['title'],
                description=request.form['description'],
                required_skills=request.form['required_skills'],
                location=request.form['location'],
                budget_min=float(request.form['budget_min']) if request.form['budget_min'] else None,
                budget_max=float(request.form['budget_max']) if request.form['budget_max'] else None,
                profession_type=request.form['profession_type']
            )

            if request.form['deadline']:
                job.deadline = datetime.strptime(request.form['deadline'], '%Y-%m-%d').date()

            db.session.add(job)
            db.session.commit()

            # Run smart matching
            try:
                matches = matching_engine.find_matches(job)
                for match in matches:
                    db.session.add(match)
                db.session.commit()

                flash(f'Job posted successfully! Found {len(matches)} potential matches.', 'success')
            except Exception as e:
                app.logger.error(f"Matching engine error: {e}")
                flash('Job posted, but matching system encountered an error.', 'warning')

            return redirect(url_for('customer_dashboard'))

        return render_template('job_post.html')

    except Exception as e:
        app.logger.error(f"Error in post_job: {e}")
        return jsonify({"error": str(e)}), 500

           

@app.route('/job/<int:job_id>')
@login_required
def job_detail(job_id):
    job = Job.query.get_or_404(job_id)
    
    # Check permissions
    if current_user.role == UserRole.customer and job.customer_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('customer_dashboard'))
    
    applications = []
    user_application = None
    
    if current_user.role == UserRole.customer:
        applications = JobApplication.query.filter_by(job_id=job.id).all()
    elif current_user.role == [UserRole.fundi, UserRole.proffesional]:
        user_application = JobApplication.query.filter_by(job_id=job.id, applicant_id=current_user.id).first()
    
    return render_template('job_detail.html', job=job, applications=applications, user_application=user_application)

@app.route('/job/<int:job_id>/apply', methods=['POST'])
@login_required
def apply_job(job_id):
    if current_user.role not in [UserRole.fundi, UserRole.proffesional]:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    job = Job.query.get_or_404(job_id)
    
    # Check if already applied
    existing_application = JobApplication.query.filter_by(job_id=job_id, applicant_id=current_user.id).first()
    if existing_application:
        flash('You have already applied for this job', 'warning')
        return redirect(url_for('job_detail', job_id=job_id))
    
    application = JobApplication(
        job_id=job_id,
        applicant_id=current_user.id,
        cover_letter=request.form['cover_letter'],
        proposed_rate=float(request.form['proposed_rate']) if request.form['proposed_rate'] else None,
        estimated_duration=request.form['estimated_duration']
    )
    
    db.session.add(application)
    db.session.commit()
    
    flash('Application submitted successfully!', 'success')
    return redirect(url_for('job_detail', job_id=job_id))

@app.route('/job/<int:job_id>/autofill')
@login_required
def autofill_application(job_id):
    if current_user.role not in [UserRole.fundi, UserRole.proffesional]:
        flash('Access denied', 'error')
        # return redirect(url_for('index'))
        return jsonify({'error': 'Access denied'}), 403
    
    job = Job.query.get_or_404(job_id)
    profile = current_user.service_provider_profile
    
    try:
        autofill_data = autofill_agent.generate_application_data(job, profile)
        return jsonify(autofill_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if current_user.role not in [UserRole.fundi, UserRole.proffesional]:
        # flash('Access denied', 'error')
        # return redirect(url_for('index'))
            profile = current_user.service_provider_profile
            if not profile:
                profile = ServiceProviderProfile(user_id=current_user.id)
                db.session.add(profile)
            
            profile.specialization = request.form['specialization']
            profile.experience_years = int(request.form['experience_years']) if request.form['experience_years'] else None
            profile.skills = request.form['skills']
            profile.location = request.form['location']
            profile.hourly_rate = float(request.form['hourly_rate']) if request.form['hourly_rate'] else None
            profile.bio = request.form['bio']
            
        elif current_user.role == 'customer':
            profile = current_user.customer_profile
            if not profile:
                profile = CustomerProfile(user_id=current_user.id)
                db.session.add(profile)
            
            profile.company_name = request.form['company_name']
            profile.location = request.form['location']
            profile.phone = request.form['phone']
            profile.preferred_budget_range = request.form['preferred_budget_range']
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

@app.route('/sales-dashboard')
@login_required
def sales_dashboard():
    if current_user.role not in [UserRole.fundi, UserRole.proffesional]:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    # Get completed jobs for this service provider
    completed_applications = JobApplication.query.filter_by(
        applicant_id=current_user.id,
        status='accepted'
    ).join(Job).filter(Job.status == 'completed').all()
    
    # Calculate earnings and statistics
    total_earnings = sum([app.proposed_rate or 0 for app in completed_applications])
    completed_jobs = len(completed_applications)
    
    # Get active jobs
    active_applications = JobApplication.query.filter_by(
        applicant_id=current_user.id,
        status='accepted'
    ).join(Job).filter(Job.status == 'in_progress').all()
    active_jobs = len(active_applications)
    
    # Calculate monthly earnings (current month)
    from datetime import datetime
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_completed = [app for app in completed_applications 
                        if app.created_at.month == current_month and app.created_at.year == current_year]
    monthly_earnings = sum([app.proposed_rate or 0 for app in monthly_completed])
    
    # Platform fees (10%)
    platform_fees = total_earnings * 0.1
    net_earnings = total_earnings - platform_fees
    
    # Calculate success rate
    all_applications = JobApplication.query.filter_by(applicant_id=current_user.id).all()
    success_rate = (completed_jobs / len(all_applications) * 100) if all_applications else 0
    
    # Get recent completed jobs (last 5)
    recent_completed_jobs = Job.query.join(JobApplication).filter(
        JobApplication.applicant_id == current_user.id,
        JobApplication.status == 'accepted',
        Job.status == 'completed'
    ).order_by(Job.updated_at.desc()).limit(5).all()
    
    return render_template('sales_dashboard.html',
                         total_earnings=total_earnings,
                         completed_jobs=completed_jobs,
                         active_jobs=active_jobs,
                         monthly_earnings=monthly_earnings,
                         platform_fees=platform_fees,
                         net_earnings=net_earnings,
                         success_rate=success_rate,
                         recent_completed_jobs=recent_completed_jobs,
                         avg_rating=4.5,  # This would come from a ratings system
                         repeat_customers=0,  # This would be calculated from customer relationships
                         avg_response_time='2 hours')

@app.route('/upload-document', methods=['POST'])
@login_required
def upload_document():
    if current_user.role not in [UserRole.fundi, UserRole.proffesional]:
        # flash('Access denied', 'error')
        # return redirect(url_for('index'))
        return jsonify({'error': 'Access denied'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file selected'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_')
        filename = timestamp + filename
        
        # Ensure upload directory exists
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process document
        try:
            extracted_text = doc_processor.extract_text(file_path)
            ai_analysis = doc_processor.analyze_document(extracted_text, request.form.get('document_type', 'general'))
            
            # Save document record
            document = Document(
                service_provider_id=current_user.service_provider_profile.id,
                filename=filename,
                original_filename=file.filename,
                file_path=file_path,
                document_type=request.form.get('document_type', 'general'),
                extracted_text=extracted_text,
                ai_analysis=json.dumps(ai_analysis)
            )
            db.session.add(document)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Document uploaded and processed successfully',
                'analysis': ai_analysis
            })
            
        except Exception as e:
            return jsonify({'error': f'Document processing failed: {str(e)}'}), 500

@app.route('/network', methods=['GET', 'POST'])
@login_required
def provider_network():
    if current_user.role not in [UserRole.fundi, UserRole.proffesional]:
        flash('Access denied', 'error')
        return redirect(url_for('index'))

    search = request.args.get('search', '')
    profession = request.args.get('profession', '')
    location = request.args.get('location', '')

    query = User.query.filter(
        User.role.in_([UserRole.fundi.value, UserRole.proffesional.value]),
        User.is_approved == True,
        User.id != current_user.id
    ).join(ServiceProviderProfile)

    if search:
        query = query.filter(
            or_(
                ServiceProviderProfile.specialization.ilike(f'%{search}%'),
                ServiceProviderProfile.skills.ilike(f'%{search}%'),
                User.username.ilike(f'%{search}%')
            )
        )

    if profession:
        query = query.filter(ServiceProviderProfile.profession == profession)

    if location:
        query = query.filter(ServiceProviderProfile.location.ilike(f'%{location}%'))

    service_providers = query.limit(24).all()

    # Compute thread IDs
    service_providers_with_threads = []
    for provider in service_providers:
        thread_id = f"{min(current_user.id, provider.id)}_{max(current_user.id, provider.id)}"
        service_providers_with_threads.append({
            'provider': provider,
            'thread_id': thread_id
        })

    total_fundis = User.query.join(ServiceProviderProfile).filter(
        User.role.in_([UserRole.fundi.value, UserRole.proffesional.value]),
        User.is_approved == True,
        ServiceProviderProfile.profession == UserRole.fundi.value
    ).count()

    total_professionals = User.query.join(ServiceProviderProfile).filter(
        User.role.in_([UserRole.fundi.value, UserRole.proffesional.value]),
        User.is_approved == True,
        ServiceProviderProfile.profession == UserRole.proffesional.value
    ).count()

    connections = []
    pending_requests = []

    return render_template(
        'provider_network.html',
        service_providers=service_providers_with_threads,
        connections=connections,
        pending_requests=pending_requests,
        total_fundis=total_fundis,
        total_professionals=total_professionals
    )


@app.route('/messages', methods=['GET', 'POST'])
@login_required
def messages():
    if current_user.role not in [UserRole.fundi, UserRole.proffesional]:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    selected_thread = request.args.get('thread')
    
    # Get all conversations for current user
    conversations = db.session.query(Message).filter(
        db.or_(
            Message.sender_id == current_user.id,
            Message.recipient_id == current_user.id
        )
    ).order_by(Message.created_at.desc()).all()
    
    # Group by thread_id and get latest message from each thread
    thread_latest = {}
    for msg in conversations:
        if msg.thread_id not in thread_latest:
            thread_latest[msg.thread_id] = msg
    
    conversations = list(thread_latest.values())
    
    # Get messages for selected thread
    thread_messages = []
    thread_recipient_id = None
    if selected_thread:
        thread_messages = Message.query.filter_by(thread_id=selected_thread).order_by(Message.created_at.asc()).all()
        if thread_messages:
            # Mark messages as read
            for msg in thread_messages:
                if msg.recipient_id == current_user.id:
                    msg.is_read = True
            db.session.commit()
            
            # Get recipient ID for replies
            for msg in thread_messages:
                if msg.sender_id != current_user.id:
                    thread_recipient_id = msg.sender_id
                    break
                elif msg.recipient_id != current_user.id:
                    thread_recipient_id = msg.recipient_id
                    break
    
    return render_template('messages.html',
                         conversations=conversations,
                         selected_thread=selected_thread,
                         thread_messages=thread_messages,
                         thread_recipient_id=thread_recipient_id)

@app.route('/send-reply/<int:recipient_id>')
@login_required
def send_message(recipient_id):
    if current_user.role not in [UserRole.fundi, UserRole.proffesional]:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    recipient = User.query.get_or_404(recipient_id)
    if recipient.role not in [UserRole.fundi.value, UserRole.proffesional.value]:
        flash('You can only message other service providers', 'error')
        return redirect(url_for('provider_network'))
    
    # Create thread ID
    thread_id = f"{min(current_user.id, recipient_id)}_{max(current_user.id, recipient_id)}"
    
    return redirect(url_for('messages', thread=thread_id))

@app.route('/send-reply', methods=['POST'])
@login_required
def send_reply():
    if current_user.role not in [UserRole.fundi, UserRole.proffesional]:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    
    thread_id = request.form.get('thread_id')
    recipient_id = int(request.form.get('recipient_id'))
    content = request.form.get('content')
    
    # Validate recipient exists and is a service provider
    recipient = User.query.get_or_404(recipient_id)
    if recipient.role not in [UserRole.fundi.value, UserRole.proffesional.value]:
        flash('You can only message other service providers', 'error')
        return redirect(url_for('provider_network'))
    
    if not content or not content.strip():
        flash('Message cannot be empty', 'error')
        return redirect(url_for('messages', thread=thread_id))
    
    # Create message
    message = Message(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=content,
        thread_id=thread_id,
        subject='Re: Conversation'
    )
    
    db.session.add(message)
    db.session.commit()
    
    flash('Message sent successfully!', 'success')
    return redirect(url_for('messages', thread=thread_id))@app.errorhandler(404)

def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
