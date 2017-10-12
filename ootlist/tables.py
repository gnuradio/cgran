import django_tables2 as tables
from .models import Outoftreemodule
from django_tables2.utils import A  # alias for Accessor
from django_tables2 import SingleTableView

class OutoftreemoduleTable(tables.Table):
    name = tables.TemplateColumn('<a href="{% url \'ootlist:oot_page\' record.id %}">{{record.name}}</a>') # links to oot_page
    tags = tables.Column(verbose_name='Categories')
    description = tables.Column(orderable=False) # no reason to ever sort by description imo
    last_commit = tables.Column(verbose_name='Most Recent Commit')
    
    ''' this used the value of the status field to color the row, but it didn't look great
    def render_status(self, value, column):
        if value == 'maintained':
            column.attrs = {'td': {'bgcolor': 'lightgreen'}}
        elif value == 'undetermined':
            column.attrs = {'td': {'bgcolor': 'lightyellow'}}
        elif value == 'weak support':
            column.attrs = {'td': {'bgcolor': 'ffcccc'}}
        else:
            column.attrs = {'td': {}}
        return value
    '''
            
    class Meta:
        model = Outoftreemodule
        fields = ('name', 'last_commit', 'description', 'tags') # fields to display
        attrs = {'class': 'table table-condensed'} # uses bootstrap table style
