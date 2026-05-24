from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import PermissionDenied
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import CommentForm, ProjectForm, TaskForm, TeamForm, TeamMembershipForm
from .models import Project, Task, Team, TeamMembership


User = get_user_model()


def _parse_pk(value):
    try:
        pk = int(value)
    except (TypeError, ValueError):
        return None
    return pk if pk > 0 else None


def _safe_return_url(request):
    candidate = request.GET.get('return', '')
    if candidate and url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}
    ):
        return candidate
    return reverse('task_list')


def _apply_task_filters(request):
    queryset = Task.objects.select_related('assigned_to', 'project')
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    project_raw = request.GET.get('project', '').strip()
    assignee_raw = request.GET.get('assignee', '').strip()

    project_id = _parse_pk(project_raw)
    assignee_id = _parse_pk(assignee_raw)

    if query:
        queryset = queryset.filter(description__icontains=query)
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    if project_id is not None:
        queryset = queryset.filter(project_id=project_id)

    if assignee_raw == 'me' and request.user.is_authenticated:
        queryset = queryset.filter(assigned_to_id=request.user.id)
    elif assignee_raw == 'unassigned':
        queryset = queryset.filter(assigned_to__isnull=True)
    elif assignee_id is not None:
        queryset = queryset.filter(assigned_to_id=assignee_id)

    context = {
        'query': query,
        'status': status_filter,
        'project_id': project_id,
        'assignee_id': assignee_id,
        'assignee_raw': assignee_raw,
        'status_choices': Task.STATUS_CHOICES,
        'projects': Project.objects.all().order_by('name'),
        'assignees': User.objects.filter(tasks__isnull=False).distinct().order_by('username'),
        'current_view': 'list',
    }
    return queryset, context


def register(request):
    if request.user.is_authenticated:
        return redirect('task_list')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('task_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


@login_required
def task_list(request):
    queryset, context = _apply_task_filters(request)
    queryset = queryset.order_by(F('deadline').asc(nulls_last=True), '-created_at')
    context['tasks'] = queryset
    context['current_view'] = 'list'
    return render(request, 'project_app/task_list.html', context)


@login_required
def task_board(request):
    queryset, context = _apply_task_filters(request)
    tasks = list(queryset)
    columns = [
        {
            'key': value,
            'label': label,
            'tasks': [t for t in tasks if t.status == value],
        }
        for value, label in Task.STATUS_CHOICES
    ]
    context['columns'] = columns
    context['current_view'] = 'board'
    return render(request, 'project_app/task_board.html', context)


@login_required
def task_detail(request, pk: int):
    task = get_object_or_404(
        Task.objects.select_related('assigned_to', 'project').prefetch_related('comments__author'),
        pk=pk,
    )
    comment_form = CommentForm()
    back_url = _safe_return_url(request)

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
            redirect_url = task.get_absolute_url()
            if request.GET.get('return'):
                redirect_url += f"?return={request.GET['return']}"
            return redirect(redirect_url)

    return render(request, 'project_app/task_detail.html', {
        'task': task,
        'comment_form': comment_form,
        'back_url': back_url,
    })


@login_required
def task_create(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save()
            return redirect(task.get_absolute_url())
    else:
        form = TaskForm()

    return render(request, 'project_app/task_form.html', {'form': form, 'mode': 'create'})


@login_required
def task_update(request, pk: int):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect(task.get_absolute_url())
    else:
        form = TaskForm(instance=task)

    return render(request, 'project_app/task_form.html', {'form': form, 'mode': 'edit'})


@login_required
def task_delete(request, pk: int):
    task = get_object_or_404(Task, pk=pk)
    if request.method == 'POST':
        task.delete()
        return redirect('task_list')

    return render(request, 'project_app/task_confirm_delete.html', {'task': task})


@login_required
def project_list(request):
    projects = Project.objects.all()
    return render(request, 'project_app/project_list.html', {'projects': projects})


@login_required
def project_detail(request, pk: int):
    project = get_object_or_404(
        Project.objects.prefetch_related('tasks__assigned_to'),
        pk=pk,
    )
    return render(request, 'project_app/project_detail.html', {'project': project})


@login_required
def project_create(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save()
            return redirect(project.get_absolute_url())
    else:
        form = ProjectForm()

    return render(request, 'project_app/project_form.html', {'form': form, 'mode': 'create'})


@login_required
def project_update(request, pk: int):
    project = get_object_or_404(Project, pk=pk)
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            return redirect(project.get_absolute_url())
    else:
        form = ProjectForm(instance=project)

    return render(request, 'project_app/project_form.html', {'form': form, 'mode': 'edit'})


@login_required
def team_list(request):
    teams = Team.objects.filter(members=request.user).distinct()
    return render(request, 'project_app/team_list.html', {'teams': teams})


@login_required
def team_create(request):
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save()
            TeamMembership.objects.create(
                team=team,
                user=request.user,
                role=TeamMembership.ROLE_MANAGER,
            )
            return redirect(team.get_absolute_url())
    else:
        form = TeamForm()
    return render(request, 'project_app/team_form.html', {'form': form, 'mode': 'create'})


@login_required
def team_detail(request, pk: int):
    team = get_object_or_404(Team.objects.prefetch_related('memberships__user'), pk=pk)
    if not team.has_member(request.user):
        raise PermissionDenied("You are not a member of this team.")

    is_manager = team.is_manager(request.user)
    add_form = TeamMembershipForm(team=team) if is_manager else None
    return render(request, 'project_app/team_detail.html', {
        'team': team,
        'is_manager': is_manager,
        'add_form': add_form,
        'roles': TeamMembership.ROLE_CHOICES,
    })


@login_required
def team_update(request, pk: int):
    team = get_object_or_404(Team, pk=pk)
    if not team.is_manager(request.user):
        raise PermissionDenied("Only managers can edit a team.")

    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            form.save()
            return redirect(team.get_absolute_url())
    else:
        form = TeamForm(instance=team)
    return render(request, 'project_app/team_form.html', {'form': form, 'mode': 'edit', 'team': team})


@login_required
@require_POST
def team_member_add(request, pk: int):
    team = get_object_or_404(Team, pk=pk)
    if not team.is_manager(request.user):
        raise PermissionDenied("Only managers can add members.")

    form = TeamMembershipForm(request.POST, team=team)
    if form.is_valid():
        membership = form.save(commit=False)
        membership.team = team
        membership.save()
    return redirect(team.get_absolute_url())


@login_required
@require_POST
def team_member_remove(request, pk: int, membership_id: int):
    team = get_object_or_404(Team, pk=pk)
    if not team.is_manager(request.user):
        raise PermissionDenied("Only managers can remove members.")

    membership = get_object_or_404(TeamMembership, pk=membership_id, team=team)
    if membership.user_id == request.user.id and team.memberships.filter(role=TeamMembership.ROLE_MANAGER).count() == 1:
        raise PermissionDenied("Cannot remove the last manager.")
    membership.delete()
    return redirect(team.get_absolute_url())


@login_required
@require_POST
def team_member_role(request, pk: int, membership_id: int):
    team = get_object_or_404(Team, pk=pk)
    if not team.is_manager(request.user):
        raise PermissionDenied("Only managers can change roles.")

    membership = get_object_or_404(TeamMembership, pk=membership_id, team=team)
    new_role = request.POST.get('role')
    valid_roles = {value for value, _ in TeamMembership.ROLE_CHOICES}
    if new_role not in valid_roles:
        raise PermissionDenied("Invalid role.")
    if (
        membership.role == TeamMembership.ROLE_MANAGER
        and new_role != TeamMembership.ROLE_MANAGER
        and team.memberships.filter(role=TeamMembership.ROLE_MANAGER).count() == 1
    ):
        raise PermissionDenied("Cannot demote the last manager.")
    membership.role = new_role
    membership.save()
    return redirect(team.get_absolute_url())
