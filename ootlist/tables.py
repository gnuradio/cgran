import django_tables2 as tables
from .models import Outoftreemodule
from django_tables2.utils import A  # alias for Accessor
from django_tables2 import SingleTableView

class OutoftreemoduleTable(tables.Table):
    name = tables.TemplateColumn('<a href="{{record.repo}}">{{record.name}}</a>')
    tags = tables.Column(verbose_name='Categories')
    #status = tables.Column()
    description = tables.Column(orderable=False) # no reason to ever sort by description imo
    last_commit = tables.Column(verbose_name='Most Recent Commit')
    
    '''
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
