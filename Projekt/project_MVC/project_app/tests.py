from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from project_app.forms import CommentForm, ProjectForm, TaskForm, TeamForm
from project_app.models import Comment, Project, Task, Team, TeamMembership


User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='tester', password='pass12345')


@pytest.fixture
def auth_client(user):
    client = Client()
    client.login(username='tester', password='pass12345')
    return client


@pytest.fixture
def project(db):
    return Project.objects.create(name='Demo', description='Demo project')


@pytest.fixture
def task(project, user):
    return Task.objects.create(
        description='Initial task',
        assigned_to=user,
        status=Task.STATUS_TODO,
        project=project,
    )


class TestModels:
    @pytest.mark.django_db
    def test_project_str(self, project):
        assert str(project) == 'Demo'

    @pytest.mark.django_db
    def test_task_str(self, task):
        assert str(task) == 'Initial task'

    @pytest.mark.django_db
    def test_task_default_status(self, project):
        t = Task.objects.create(description='Another', project=project)
        assert t.status == Task.STATUS_TODO


class TestForms:
    @pytest.mark.django_db
    def test_task_form_valid(self, project, user):
        form = TaskForm(data={
            'description': 'Write docs',
            'assigned_to': user.pk,
            'status': Task.STATUS_TODO,
            'project': project.pk,
        })
        assert form.is_valid(), form.errors

    @pytest.mark.django_db
    def test_task_form_accepts_details(self, project, user):
        form = TaskForm(data={
            'description': 'Write docs',
            'details': 'Detailed multi-line\nbody of the task.',
            'assigned_to': user.pk,
            'status': Task.STATUS_TODO,
            'project': project.pk,
        })
        assert form.is_valid(), form.errors
        task = form.save()
        assert task.details.startswith('Detailed multi-line')

    @pytest.mark.django_db
    def test_task_details_optional(self, project, user):
        form = TaskForm(data={
            'description': 'Write docs',
            'details': '',
            'assigned_to': user.pk,
            'status': Task.STATUS_TODO,
            'project': project.pk,
        })
        assert form.is_valid()

    @pytest.mark.django_db
    def test_task_form_description_too_short(self, project):
        form = TaskForm(data={
            'description': 'ab',
            'assigned_to': '',
            'status': Task.STATUS_TODO,
            'project': project.pk,
        })
        assert not form.is_valid()
        assert 'description' in form.errors

    @pytest.mark.django_db
    def test_project_form_invalid_blank_name(self):
        form = ProjectForm(data={'name': '   ', 'description': 'x'})
        assert not form.is_valid()
        assert 'name' in form.errors

    @pytest.mark.django_db
    def test_comment_form_valid(self):
        form = CommentForm(data={'body': 'A comment'})
        assert form.is_valid()

    @pytest.mark.django_db
    def test_comment_form_invalid_blank(self):
        form = CommentForm(data={'body': '   '})
        assert not form.is_valid()


class TestViews:
    @pytest.mark.django_db
    def test_task_list_redirects_anonymous(self, client):
        response = client.get(reverse('task_list'))
        assert response.status_code == 302
        assert '/login' in response.url

    @pytest.mark.django_db
    def test_task_list_returns_200_and_contains_task(self, auth_client, task):
        response = auth_client.get(reverse('task_list'))
        assert response.status_code == 200
        assert task.description.encode() in response.content

    @pytest.mark.django_db
    def test_task_list_search_filter(self, auth_client, project):
        Task.objects.create(description='Alpha task', project=project)
        Task.objects.create(description='Beta task', project=project)
        response = auth_client.get(reverse('task_list'), {'q': 'Alpha'})
        assert response.status_code == 200
        assert b'Alpha task' in response.content
        assert b'Beta task' not in response.content

    @pytest.mark.django_db
    def test_task_list_status_filter(self, auth_client, project):
        Task.objects.create(description='Open one', project=project, status=Task.STATUS_TODO)
        Task.objects.create(description='Done one', project=project, status=Task.STATUS_DONE)
        response = auth_client.get(reverse('task_list'), {'status': Task.STATUS_DONE})
        assert b'Done one' in response.content
        assert b'Open one' not in response.content

    @pytest.mark.django_db
    def test_task_create_requires_login(self, client):
        response = client.get(reverse('task_create'))
        assert response.status_code == 302
        assert '/login' in response.url

    @pytest.mark.django_db
    def test_task_create_saves_with_auth(self, auth_client, project):
        response = auth_client.post(reverse('task_create'), {
            'description': 'Brand new task',
            'assigned_to': '',
            'status': Task.STATUS_TODO,
            'project': project.pk,
        })
        assert response.status_code == 302
        assert Task.objects.filter(description='Brand new task').exists()

    @pytest.mark.django_db
    def test_task_update_changes_record(self, auth_client, task, project):
        response = auth_client.post(reverse('task_update', args=[task.pk]), {
            'description': 'Updated description',
            'assigned_to': '',
            'status': Task.STATUS_IN_PROGRESS,
            'project': project.pk,
        })
        assert response.status_code == 302
        task.refresh_from_db()
        assert task.description == 'Updated description'
        assert task.status == Task.STATUS_IN_PROGRESS

    @pytest.mark.django_db
    def test_task_delete_removes_record(self, auth_client, task):
        response = auth_client.post(reverse('task_delete', args=[task.pk]))
        assert response.status_code == 302
        assert not Task.objects.filter(pk=task.pk).exists()

    @pytest.mark.django_db
    def test_task_detail_redirects_anonymous(self, client, task):
        response = client.get(reverse('task_detail', args=[task.pk]))
        assert response.status_code == 302
        assert '/login' in response.url

    @pytest.mark.django_db
    def test_task_detail_get(self, auth_client, task):
        response = auth_client.get(reverse('task_detail', args=[task.pk]))
        assert response.status_code == 200
        assert task.description.encode() in response.content

    @pytest.mark.django_db
    def test_task_detail_post_adds_comment(self, auth_client, task):
        response = auth_client.post(reverse('task_detail', args=[task.pk]), {
            'body': 'Looks great',
        })
        assert response.status_code == 302
        assert Comment.objects.filter(task=task, body='Looks great').exists()

    @pytest.mark.django_db
    def test_task_detail_breadcrumb_uses_return_param(self, auth_client, task):
        url = reverse('task_detail', args=[task.pk]) + '?return=/%3Fstatus%3Ddone'
        response = auth_client.get(url)
        assert response.status_code == 200
        assert b'/?status=done' in response.content

    @pytest.mark.django_db
    def test_task_detail_breadcrumb_rejects_external(self, auth_client, task):
        url = reverse('task_detail', args=[task.pk]) + '?return=https://evil.example/'
        response = auth_client.get(url)
        assert response.status_code == 200
        assert b'evil.example' not in response.content

    @pytest.mark.django_db
    def test_task_list_link_includes_return_param(self, auth_client, task):
        response = auth_client.get(reverse('task_list'), {'status': 'todo'})
        assert response.status_code == 200
        assert b'return=' in response.content

    @pytest.mark.django_db
    def test_task_detail_shows_details(self, auth_client, project, user):
        task = Task.objects.create(
            description='Has body',
            details='A longer\nmulti-line body.',
            project=project,
            assigned_to=user,
        )
        response = auth_client.get(reverse('task_detail', args=[task.pk]))
        assert response.status_code == 200
        assert b'longer' in response.content

    @pytest.mark.django_db
    def test_project_list_redirects_anonymous(self, client):
        response = client.get(reverse('project_list'))
        assert response.status_code == 302
        assert '/login' in response.url

    @pytest.mark.django_db
    def test_project_list_200(self, auth_client, project):
        response = auth_client.get(reverse('project_list'))
        assert response.status_code == 200
        assert project.name.encode() in response.content

    @pytest.mark.django_db
    def test_project_create_requires_login(self, client):
        response = client.get(reverse('project_create'))
        assert response.status_code == 302
        assert '/login' in response.url

    @pytest.mark.django_db
    def test_project_create_saves_with_auth(self, auth_client):
        response = auth_client.post(reverse('project_create'), {
            'name': 'New Project',
            'description': 'desc',
        })
        assert response.status_code == 302
        assert Project.objects.filter(name='New Project').exists()


class TestRegister:
    @pytest.mark.django_db
    def test_register_page_is_public(self, client):
        response = client.get(reverse('register'))
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_register_creates_user_and_logs_in(self, client):
        response = client.post(reverse('register'), {
            'username': 'newbie',
            'password1': 'strongpass987',
            'password2': 'strongpass987',
        })
        assert response.status_code == 302
        assert User.objects.filter(username='newbie').exists()
        assert response.wsgi_request.user.is_authenticated

    @pytest.mark.django_db
    def test_register_rejects_password_mismatch(self, client):
        response = client.post(reverse('register'), {
            'username': 'mismatch',
            'password1': 'strongpass987',
            'password2': 'different987',
        })
        assert response.status_code == 200
        assert not User.objects.filter(username='mismatch').exists()

    @pytest.mark.django_db
    def test_authenticated_user_redirected_from_register(self, auth_client):
        response = auth_client.get(reverse('register'))
        assert response.status_code == 302


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username='other', password='pass12345')


@pytest.fixture
def team(user):
    team = Team.objects.create(name='Backend', description='Backend team')
    TeamMembership.objects.create(team=team, user=user, role=TeamMembership.ROLE_MANAGER)
    return team


@pytest.fixture
def member_user(team):
    member = User.objects.create_user(username='member1', password='pass12345')
    TeamMembership.objects.create(team=team, user=member, role=TeamMembership.ROLE_MEMBER)
    return member


class TestTeamModels:
    @pytest.mark.django_db
    def test_team_str(self, team):
        assert str(team) == 'Backend'

    @pytest.mark.django_db
    def test_is_manager_true(self, team, user):
        assert team.is_manager(user) is True

    @pytest.mark.django_db
    def test_is_manager_false_for_member(self, team, member_user):
        assert team.is_manager(member_user) is False

    @pytest.mark.django_db
    def test_has_member(self, team, user, other_user):
        assert team.has_member(user) is True
        assert team.has_member(other_user) is False


class TestTeamForms:
    @pytest.mark.django_db
    def test_team_form_valid(self):
        assert TeamForm(data={'name': 'Frontend', 'description': ''}).is_valid()

    @pytest.mark.django_db
    def test_team_form_blank_name(self):
        form = TeamForm(data={'name': '   ', 'description': ''})
        assert not form.is_valid()
        assert 'name' in form.errors

    @pytest.mark.django_db
    def test_team_form_unique_name(self, team):
        form = TeamForm(data={'name': 'Backend', 'description': ''})
        assert not form.is_valid()


class TestTeamViews:
    @pytest.mark.django_db
    def test_team_list_redirects_anonymous(self, client):
        response = client.get(reverse('team_list'))
        assert response.status_code == 302
        assert '/login' in response.url

    @pytest.mark.django_db
    def test_team_list_shows_only_user_teams(self, auth_client, user, team):
        other = Team.objects.create(name='Detached')
        response = auth_client.get(reverse('team_list'))
        assert response.status_code == 200
        assert b'Backend' in response.content
        assert b'Detached' not in response.content

    @pytest.mark.django_db
    def test_team_create_makes_creator_manager(self, auth_client, user):
        response = auth_client.post(reverse('team_create'), {'name': 'Mobile', 'description': ''})
        assert response.status_code == 302
        team = Team.objects.get(name='Mobile')
        assert team.is_manager(user)

    @pytest.mark.django_db
    def test_non_member_cannot_view_team(self, client, team, other_user):
        client.login(username='other', password='pass12345')
        response = client.get(reverse('team_detail', args=[team.pk]))
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_member_can_view_team(self, client, team, member_user):
        client.login(username='member1', password='pass12345')
        response = client.get(reverse('team_detail', args=[team.pk]))
        assert response.status_code == 200
        assert b'Backend' in response.content

    @pytest.mark.django_db
    def test_only_manager_can_edit_team(self, client, team, member_user):
        client.login(username='member1', password='pass12345')
        response = client.post(reverse('team_update', args=[team.pk]), {'name': 'Hacked', 'description': ''})
        assert response.status_code == 403
        team.refresh_from_db()
        assert team.name == 'Backend'

    @pytest.mark.django_db
    def test_manager_can_add_member(self, auth_client, team, other_user):
        response = auth_client.post(
            reverse('team_member_add', args=[team.pk]),
            {'user': other_user.pk, 'role': TeamMembership.ROLE_MEMBER},
        )
        assert response.status_code == 302
        assert TeamMembership.objects.filter(team=team, user=other_user).exists()

    @pytest.mark.django_db
    def test_member_cannot_add_member(self, client, team, member_user, other_user):
        client.login(username='member1', password='pass12345')
        response = client.post(
            reverse('team_member_add', args=[team.pk]),
            {'user': other_user.pk, 'role': TeamMembership.ROLE_MEMBER},
        )
        assert response.status_code == 403

    @pytest.mark.django_db
    def test_manager_can_change_role(self, auth_client, team, member_user):
        membership = TeamMembership.objects.get(team=team, user=member_user)
        response = auth_client.post(
            reverse('team_member_role', args=[team.pk, membership.pk]),
            {'role': TeamMembership.ROLE_MANAGER},
        )
        assert response.status_code == 302
        membership.refresh_from_db()
        assert membership.role == TeamMembership.ROLE_MANAGER

    @pytest.mark.django_db
    def test_manager_can_remove_member(self, auth_client, team, member_user):
        membership = TeamMembership.objects.get(team=team, user=member_user)
        response = auth_client.post(reverse('team_member_remove', args=[team.pk, membership.pk]))
        assert response.status_code == 302
        assert not TeamMembership.objects.filter(pk=membership.pk).exists()

    @pytest.mark.django_db
    def test_cannot_remove_last_manager(self, auth_client, team, user):
        membership = TeamMembership.objects.get(team=team, user=user)
        response = auth_client.post(reverse('team_member_remove', args=[team.pk, membership.pk]))
        assert response.status_code == 403
        assert TeamMembership.objects.filter(pk=membership.pk).exists()

    @pytest.mark.django_db
    def test_cannot_demote_last_manager(self, auth_client, team, user):
        membership = TeamMembership.objects.get(team=team, user=user)
        response = auth_client.post(
            reverse('team_member_role', args=[team.pk, membership.pk]),
            {'role': TeamMembership.ROLE_MEMBER},
        )
        assert response.status_code == 403
        membership.refresh_from_db()
        assert membership.role == TeamMembership.ROLE_MANAGER


class TestDeadlines:
    @pytest.mark.django_db
    def test_task_overdue_when_past_and_not_done(self, project):
        yesterday = timezone.localdate() - timedelta(days=1)
        t = Task.objects.create(
            description='Late task',
            project=project,
            status=Task.STATUS_TODO,
            deadline=yesterday,
        )
        assert t.is_overdue is True

    @pytest.mark.django_db
    def test_task_not_overdue_when_done(self, project):
        yesterday = timezone.localdate() - timedelta(days=1)
        t = Task.objects.create(
            description='Closed task',
            project=project,
            status=Task.STATUS_DONE,
            deadline=yesterday,
        )
        assert t.is_overdue is False

    @pytest.mark.django_db
    def test_task_form_accepts_deadline(self, project):
        form = TaskForm(data={
            'description': 'With deadline',
            'assigned_to': '',
            'status': Task.STATUS_TODO,
            'project': project.pk,
            'deadline': '2099-12-31',
        })
        assert form.is_valid(), form.errors


class TestTaskBoard:
    @pytest.mark.django_db
    def test_task_board_requires_login(self, client):
        response = client.get(reverse('task_board'))
        assert response.status_code == 302
        assert '/login' in response.url

    @pytest.mark.django_db
    def test_task_board_renders_columns_with_tasks(self, auth_client, project):
        Task.objects.create(description='Todo card', project=project, status=Task.STATUS_TODO)
        Task.objects.create(description='Doing card', project=project, status=Task.STATUS_IN_PROGRESS)
        Task.objects.create(description='Done card', project=project, status=Task.STATUS_DONE)

        response = auth_client.get(reverse('task_board'))
        assert response.status_code == 200
        content = response.content
        assert b'Todo card' in content
        assert b'Doing card' in content
        assert b'Done card' in content
        assert b'To do' in content
        assert b'In progress' in content
        assert b'Done' in content


class TestTaskFilters:
    @pytest.mark.django_db
    def test_task_list_filter_by_project(self, auth_client):
        p1 = Project.objects.create(name='Alpha')
        p2 = Project.objects.create(name='Bravo')
        Task.objects.create(description='Task in alpha', project=p1)
        Task.objects.create(description='Task in bravo', project=p2)

        response = auth_client.get(reverse('task_list'), {'project': p1.pk})
        assert response.status_code == 200
        assert b'Task in alpha' in response.content
        assert b'Task in bravo' not in response.content

    @pytest.mark.django_db
    def test_task_list_filter_by_assignee(self, auth_client, project):
        u1 = User.objects.create_user(username='ann', password='pass12345')
        u2 = User.objects.create_user(username='bob', password='pass12345')
        Task.objects.create(description='Ann task', project=project, assigned_to=u1)
        Task.objects.create(description='Bob task', project=project, assigned_to=u2)

        response = auth_client.get(reverse('task_list'), {'assignee': u1.pk})
        assert response.status_code == 200
        assert b'Ann task' in response.content
        assert b'Bob task' not in response.content

    @pytest.mark.django_db
    def test_task_list_filter_assignee_me(self, auth_client, user, project):
        other = User.objects.create_user(username='someone', password='pass12345')
        Task.objects.create(description='Mine task', project=project, assigned_to=user)
        Task.objects.create(description='Other task', project=project, assigned_to=other)

        response = auth_client.get(reverse('task_list'), {'assignee': 'me'})
        assert response.status_code == 200
        assert b'Mine task' in response.content
        assert b'Other task' not in response.content

    @pytest.mark.django_db
    def test_task_list_filter_assignee_unassigned(self, auth_client, user, project):
        Task.objects.create(description='Has owner', project=project, assigned_to=user)
        Task.objects.create(description='No owner', project=project, assigned_to=None)

        response = auth_client.get(reverse('task_list'), {'assignee': 'unassigned'})
        assert response.status_code == 200
        assert b'No owner' in response.content
        assert b'Has owner' not in response.content

    @pytest.mark.django_db
    def test_task_list_invalid_project_param_does_not_crash(self, auth_client, project):
        Task.objects.create(description='Some task', project=project)
        response = auth_client.get(reverse('task_list'), {'project': 'notanumber'})
        assert response.status_code == 200

    @pytest.mark.django_db
    def test_task_board_inherits_same_filters(self, auth_client, project):
        Task.objects.create(description='Match done', project=project, status=Task.STATUS_DONE)
        Task.objects.create(description='Skip todo', project=project, status=Task.STATUS_TODO)

        response = auth_client.get(reverse('task_board'), {'status': Task.STATUS_DONE})
        assert response.status_code == 200
        assert b'Match done' in response.content
        assert b'Skip todo' not in response.content
