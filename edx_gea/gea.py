"""GEA (Grade External Activity). An XBlock used to grade external activities.

All kind of student activities can't be achieved inside edx-platform. Therefore a teacher will only describe the activity in the lms and add a GEA XBlock to grade it. """ 

import csv
import pkg_resources

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext as _
from django.template import Context, Template

from webob.response import Response

from xblock.core import XBlock
from xblock.fields import Scope, String, Integer, Float
from xblock.fragment import Fragment
from xblockutils.studio_editable import StudioEditableXBlockMixin
from xblockutils.resources import ResourceLoader

from .forms import UploadAssessmentFileForm, get_default_delimiter
from .gea_assessment import GeaAssessment, Score

import logging
log = logging.getLogger(__name__)

loader = ResourceLoader(__name__)

class GradeExternalActivityXBlock(XBlock, StudioEditableXBlockMixin):
    """XBlock to grade external activities."""

    has_score = True #: This flags the XBlock as a problem.
    icon_class = 'problem'

    display_name = String(
        display_name=_('External Activity Grader'),
        default='External Activity Grader',
        scope=Scope.settings,
        help='This name appears in the horizontal navigation at the top of '
             'the page.',
    )

    points = Integer(
        display_name='Maximum grade',
        help='Maximum grade of the external activity.',
        default=10,
        scope=Scope.settings,
    )

    weight = None #: needed by courseware.grades.get_score. (We don't use it.)

    editable_fields = ('points',)

    usernames = {} #: A dict used to avoid multiple calls to db {'username' : models.User , ...}.

    max_assessment_file_lines = 1000 #: The limit of csv lines in the uploded assessment file.

    csv_delimiter = None #: The csv delimiter used in the uploaded assessment file.

    def build_fragment(
        self,
        template,
        context_dict,
    ):
        """
        Creates a fragment for display.
        """
        fragment = Fragment(self.render_template(template, context_dict))
        return fragment


    def student_view(self, context=None):
        """Display the student assessment (score and comment).
        Note:
            The LMS Runtime only calls the XBlock.student_view. In order to get two different
            views, depending on the runtime user being a staff member or a student, we check inside the student_view
            if the user is a staff and call the staff_view accordingly.
        """
        if self.is_course_staff():
            return self.staff_view()
        context = context or {}
        gea_assessment = GeaAssessment(User.objects.get(id=self.xmodule_runtime.user_id), self)
        context.update(
            {
                'score' : gea_assessment.score,
                'comment' : gea_assessment.comment,
            }
        )
        frag = self.build_fragment('templates/student.html', context)
        return frag


    def staff_view(self, context=None):
        """Display the form for uploading the assessement file."""
        context = context or {}
        spinner_url = self.runtime.local_resource_url(self, 'public/img/spinner.gif')
        context.update(
            {
                'upload_assessment_file_form' : UploadAssessmentFileForm(auto_id=True, initial={'csv_delimiter' : get_default_delimiter()}),
                'spinner_url' : spinner_url,
                'max_assessment_file_lines' : self.max_assessment_file_lines,
            }
        )
        frag = self.build_fragment('templates/staff.html', context)
        frag.add_css(self.resource_string("static/css/gea.css"))
        frag.add_javascript(self.resource_string("static/js/src/gea.js"))
        frag.initialize_js('GeaXBlock')
        return frag


    @XBlock.handler
    def upload_assessments(self, request, context=None):
        """Called when a staff has submitted an assessment file.
        Perform the file validation. If the file is valid grade students, otherwise
        return the list of errors and offer the staff to upload a new file.
        """
        if not self.is_course_staff():
            raise PermissionDenied
        uploaded_file = request.POST['file'].file
        self.csv_delimiter = request.POST['csv_delimiter']
        form = UploadAssessmentFileForm(request.POST, files={'assessment_file' : uploaded_file},
                                        auto_id=True, gea_xblock=self)
        if form.is_valid():
            self.handle_assessment_file(uploaded_file)
            return Response("<p class='gea_success'>{}</p>".format(_("Thank you, the students assessment has been done.")))
        else:
            return Response(loader.render_template("templates/form_errors.html",
                                                   {'upload_assessment_file_form' : form}))


    def handle_assessment_file(self, file):
        """Read the file and set score and comment through the GeaAssessment class.
        Note:
            We expect a csv file following this structure:
                +----------+----+------------+
                | student1 | 10 | Good work. |
                +----------+----+------------+
                | student2 | 20 | Bad work.  |
                +----------+----+------------+
        Args:
            file: The assessment file.
        """
        assessment_file = csv.DictReader(file, ['username', 'score', 'comment'],
                                         delimiter=str(self.csv_delimiter))
        for row in assessment_file:
            gea_assessment = GeaAssessment(self.usernames[row['username']], self)
            gea_assessment.comment = row['comment']
            gea_assessment.score = Score(row['score'], self.max_score())


    '''
    Util functions
    '''
    def load_resource(self, resource_path):
        '''
        Gets the content of a resource
        '''
        resource_content = pkg_resources.resource_string(__name__, resource_path)
        return str(resource_content)

    def resource_string(self, path):
        '''Handy helper for getting resources from our kit.'''
        data = pkg_resources.resource_string(__name__, path)
        return data.decode('utf8')

    def render_template(self, template_path, context={}):
        '''
        Evaluate a template by resource path, applying the provided context
        '''
        template_str = self.load_resource(template_path)
        return Template(template_str).render(Context(context))

    def is_course_staff(self):
        return getattr(self.xmodule_runtime, 'user_is_staff', False)

    def max_score(self):
        """Return the max score of the external activity.
        Also called by courseware.grades.get_score function.
        """
        return self.points
