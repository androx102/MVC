from django.contrib import admin

from .models import Comment, Project, Task, Team, TeamMembership

admin.site.register(Project)
admin.site.register(Task)
admin.site.register(Comment)
admin.site.register(Team)
admin.site.register(TeamMembership)
