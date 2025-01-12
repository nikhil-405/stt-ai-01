import json
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.trace import SpanKind
import logging

logging.basicConfig(
    filename = 'logs.log',
    level = logging.INFO,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S'
)

module_logger = logging.getLogger('ModuleLogger')

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

# OpenTelemetry Setup
resource = Resource.create({"service.name": "course-catalog-service"})
trace.set_tracer_provider(TracerProvider(resource = resource))
tracer = trace.get_tracer(__name__)

# setting up the Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name = "localhost",
    agent_port = 6831,
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
FlaskInstrumentor().instrument_app(app)    

# Utility Functions
def load_courses():
    """Load courses from the JSON file."""
    if not os.path.exists(COURSE_FILE):
        print("file not found")
        return []  
    with open(COURSE_FILE, 'r') as file:
        return json.load(file)

def save_courses(data):
    """Save new course data to the JSON file."""
    courses = load_courses()
    courses.append(data) 
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent = 4)

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/catalog')
def course_catalog():
    with tracer.start_as_current_span("Render course catalog") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("user.ip", request.remote_addr)

        courses = load_courses()
        span.set_attribute("courses.count", len(courses))
        return render_template('course_catalog.html', courses = courses)

@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    with tracer.start_as_current_span("Add Course Operation") as span:
        try:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.route", "/add_course")

            if request.method == 'POST':
                with tracer.start_as_current_span("Handle Form Data") as form_span:
                    course = {field: request.form.get(field, '').strip() for field in [
                        'code', 'name', 'instructor', 'semester', 'schedule',
                        'classroom', 'prerequisites', 'grading', 'description']}
                    form_span.set_attribute("form.data_received", json.dumps(course))

                with tracer.start_as_current_span("Validate Form Data") as validation_span:
                    missing_fields = [key for key, value in course.items() if not value]
                    if missing_fields:
                        error_message = f"Missing fields: {', '.join(missing_fields)}"
                        
                        validation_span.set_attribute("error", True)
                        validation_span.add_event("Validation Error", {
                            "missing_fields": ", ".join(missing_fields),
                            "message": error_message,
                        })

                        flash(error_message, "error")
                        return render_template('add_course.html')

                # Save course data
                with tracer.start_as_current_span("Save Course Data") as save_span:
                    try:
                        save_courses(course)
                        save_span.add_event("Course saved successfully", {"course_code": course['code']})
                    except Exception as e:
                        error_message = f"Failed to save course: {str(e)}"
                        save_span.set_attribute("error", True)
                        save_span.add_event("Database Error", {"message": error_message})
                        raise

                flash(f"Course '{course['name']}' added successfully!", "success")
                return redirect(url_for('course_catalog'))

            span.add_event("Rendered course addition form")
            return render_template('add_course.html')

        except Exception as e:
            error_message = f"Unexpected error occurred: {str(e)}"
            span.set_attribute("error", True)
            span.add_event("Unhandled Exception", {"message": error_message})
            app.logger.error(error_message)
            flash("An unexpected error occurred. Please try again later.", "error")
            return render_template('add_course.html')

@app.route('/course/<code>')
def course_details(code):
    with tracer.start_as_current_span(f"Course Code: {code}") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("user.ip", request.remote_addr)

        courses = load_courses()
        course = next((course for course in courses if course['code'] == code), None)
        if not course:
            flash(f"No course found with code '{code}'.", "error")
            return redirect(url_for('course_catalog'))
        return render_template('course_details.html', course = course)


@app.route("/manual-trace")
def manual_trace():
    with tracer.start_as_current_span("manual-span", kind = SpanKind.SERVER) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.add_event("Processing request")
        return "Manual trace recorded!", 200

@app.route("/auto-instrumented")
def auto_instrumented():
    return "This route is auto-instrumented!", 200

if __name__ == '__main__':
    app.run(debug=True)