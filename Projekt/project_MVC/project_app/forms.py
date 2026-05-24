from django import forms
from django.contrib.auth import get_user_model

from .models import Comment, Project, Task, Team, TeamMembership


User = get_user_model()


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['description', 'details', 'assigned_to', 'status', 'project', 'deadline']
        widgets = {
            'deadline': forms.DateInput(attrs={'type': 'date'}),
            'details': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Optional detailed description'}),
        }

    def clean_description(self) -> str:
        value = self.cleaned_data['description'].strip()
        if len(value) < 3:
            raise forms.ValidationError("Description must be at least 3 characters.")
        return value


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description']

    def clean_name(self) -> str:
        value = self.cleaned_data['name'].strip()
        if not value:
            raise forms.ValidationError("Name is required.")
        return value


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['body']

    def clean_body(self) -> str:
        value = self.cleaned_data['body'].strip()
        if not value:
            raise forms.ValidationError("Comment body cannot be empty.")
        return value


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'description']

    def clean_name(self) -> str:
        value = self.cleaned_data['name'].strip()
        if not value:
            raise forms.ValidationError("Name is required.")
        return value


class TeamMembershipForm(forms.ModelForm):
    class Meta:
        model = TeamMembership
        fields = ['user', 'role']

    def __init__(self, *args, team=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.team = team
        if team is not None:
            existing = team.memberships.values_list('user_id', flat=True)
            self.fields['user'].queryset = User.objects.exclude(pk__in=existing).order_by('username')

    def clean(self):
        cleaned = super().clean()
        user = cleaned.get('user')
        if self.team is not None and user is not None:
            if self.team.memberships.filter(user=user).exists():
                raise forms.ValidationError("User is already in this team.")
        return cleaned
