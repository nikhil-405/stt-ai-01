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

# Flask App Initialization
os.environ['FLASK_ENV'] = 'production'
app = Flask(__name__)
app.secret_key = 'secret'
COURSE_FILE = 'course_catalog.json'

# OpenTelemetry Setup
resource = Resource.create({"service.name": "course-catalog-service"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
FlaskInstrumentor().instrument_app(app)    

# Utility Functions
def load_courses():
    """Load courses from the JSON file."""
    if not os.path.exists(COURSE_FILE):
        print("file not found")
        return []  # Return an empty list if the file doesn't exist
    with open(COURSE_FILE, 'r') as file:
        return json.load(file)


def save_courses(data):
    """Save new course data to the JSON file."""
    courses = load_courses()  # Load existing courses
    courses.append(data)  # Append the new course
    with open(COURSE_FILE, 'w') as file:
        json.dump(courses, file, indent = 4)


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/catalog')
def course_catalog():
    courses = load_courses()
    return render_template('course_catalog.html', courses=courses)


@app.route('/add_course', methods=['GET', 'POST'])
def add_course():
    if request.method == 'POST':
        course = {
            'code': request.form['code'],
            'name': request.form['name'],
            'instructor': request.form['instructor'],
            'semester': request.form['semester'],
            'schedule': request.form['schedule'],
            'classroom': request.form['classroom'],
            'prerequisites': request.form['prerequisites'],
            'grading': request.form['grading'],
            'description': request.form['description']
        }

        # Checking if required fields are missing
        for attribute in course.keys():
            if course[attribute] == "":
                # notifying the user
                flash(f"'{attribute}' is required.", "error")

                # logging the error
                logging.basicConfig(filename = 'logs.log', 
                        level = logging.ERROR, 
                        format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt = '%Y-%m-%d %H:%M:%S')

                module_logger = logging.getLogger('ModuleLogger')
                module_logger.error(f"'{attribute}' was not added by the user.")
                
                # Resetting the logging configuration
                logging.basicConfig(level = logging.INFO, 
                        format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt = '%Y-%m-%d %H:%M:%S')
                return render_template('add_course.html')
        
        # all fields are present
        save_courses(course)
        flash(f"Course '{course['name']}' added successfully!", "success")

        logging.basicConfig(filename = 'logs.log', 
                        level = logging.INFO, 
                        format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        datefmt = '%Y-%m-%d %H:%M:%S')

        module_logger = logging.getLogger('ModuleLogger')
        module_logger.info(f"Course '{course['name']}' added successfully!")

        # resetting the logging configuration
        logging.basicConfig(level = logging.INFO, 
                format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt = '%Y-%m-%d %H:%M:%S')
        return redirect(url_for('course_catalog'))
    return render_template('add_course.html')


@app.route('/course/<code>')
def course_details(code):
    courses = load_courses()
    course = next((course for course in courses if course['code'] == code), None)
    if not course:
        flash(f"No course found with code '{code}'.", "error")
        return redirect(url_for('course_catalog'))
    return render_template('course_details.html', course=course)


@app.route("/manual-trace")
def manual_trace():
    # Start a span manually for custom tracing
    with tracer.start_as_current_span("manual-span", kind=SpanKind.SERVER) as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", request.url)
        span.add_event("Processing request")
        return "Manual trace recorded!", 200

@app.route("/auto-instrumented")
def auto_instrumented():
    # Automatically instrumented via FlaskInstrumentor
    return "This route is auto-instrumented!", 200

if __name__ == '__main__':
    app.run(debug=True)