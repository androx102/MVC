import re

import pytest
from django.contrib.auth import get_user_model
from playwright.sync_api import expect, sync_playwright

from project_app.models import Project, Task, Team, TeamMembership


User = get_user_model()


@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()


def _login(page, live_server, username, password):
    page.goto(f'{live_server.url}/login/')
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.get_by_role('button', name='Sign in').click()


@pytest.mark.django_db(transaction=True)
def test_anonymous_visitor_redirected_to_login(page, live_server):
    page.goto(live_server.url)
    expect(page).to_have_url(f'{live_server.url}/login/?next=/')


@pytest.mark.django_db(transaction=True)
def test_logged_in_user_sees_task_list(page, live_server):
    User.objects.create_user(username='alice', password='secret123')
    project = Project.objects.create(name='E2E Project')
    Task.objects.create(description='First e2e task', project=project)
    Task.objects.create(description='Second e2e task', project=project)

    _login(page, live_server, 'alice', 'secret123')

    expect(page.locator('h2')).to_contain_text('Tasks')
    expect(page.locator('table')).to_contain_text('First e2e task')
    expect(page.locator('table')).to_contain_text('Second e2e task')


@pytest.mark.django_db(transaction=True)
def test_search_filters_tasks(page, live_server):
    User.objects.create_user(username='alice', password='secret123')
    project = Project.objects.create(name='E2E Project')
    Task.objects.create(description='Unique alpha entry', project=project)
    Task.objects.create(description='Other beta entry', project=project)

    _login(page, live_server, 'alice', 'secret123')

    page.fill('input[name="q"]', 'Unique alpha')
    page.get_by_role('button', name='Search').click()

    expect(page.locator('table')).to_contain_text('Unique alpha entry')
    expect(page.locator('table')).not_to_contain_text('Other beta entry')


@pytest.mark.django_db(transaction=True)
def test_register_flow_creates_user_and_logs_in(page, live_server):
    Project.objects.create(name='E2E Project')

    page.goto(f'{live_server.url}/register/')
    page.fill('input[name="username"]', 'fresh_user')
    page.fill('input[name="password1"]', 'strongpass987')
    page.fill('input[name="password2"]', 'strongpass987')
    page.get_by_role('button', name='Create account').click()

    expect(page.locator('h2')).to_contain_text('Tasks')
    assert User.objects.filter(username='fresh_user').exists()


@pytest.mark.django_db(transaction=True)
def test_login_and_create_task(page, live_server):
    User.objects.create_user(username='alice', password='secret123')
    Project.objects.create(name='Selectable Project')

    _login(page, live_server, 'alice', 'secret123')

    page.get_by_role('link', name='Add task').click()
    page.fill('input[name="description"]', 'Task created via e2e')
    page.locator('select[name="project"]').select_option(label='Selectable Project')
    page.get_by_role('button', name='Save').click()

    expect(page.locator('h2')).to_contain_text('Task created via e2e')
    assert Task.objects.filter(description='Task created via e2e').exists()


@pytest.mark.django_db(transaction=True)
def test_team_create_and_add_member_flow(page, live_server):
    User.objects.create_user(username='alice', password='secret123')
    User.objects.create_user(username='bob', password='secret123')

    _login(page, live_server, 'alice', 'secret123')

    page.get_by_role('link', name='Teams').click()
    page.get_by_role('link', name='Create team').click()

    page.fill('input[name="name"]', 'E2E Team')
    page.get_by_role('button', name='Save').click()

    expect(page.locator('h2')).to_contain_text('E2E Team')
    page.locator('#id_user').select_option(label='bob')
    page.locator('#id_role').select_option(value='member')
    page.get_by_role('button', name='Add member').click()

    expect(page.locator('table')).to_contain_text('bob')
    team = Team.objects.get(name='E2E Team')
    assert TeamMembership.objects.filter(team=team, user__username='bob').exists()


@pytest.mark.django_db(transaction=True)
def test_task_form_validation(page, live_server):
    User.objects.create_user(username='alice', password='secret123')
    Project.objects.create(name='Selectable Project')

    _login(page, live_server, 'alice', 'secret123')

    page.goto(f'{live_server.url}/tasks/new/')
    page.fill('input[name="description"]', 'a')
    page.locator('select[name="project"]').select_option(label='Selectable Project')
    page.get_by_role('button', name='Save').click()

    expect(page.locator('.errorlist').first).to_be_visible()
    assert not Task.objects.filter(description='a').exists()


@pytest.mark.django_db(transaction=True)
def test_breadcrumb_returns_to_filtered_list(page, live_server):
    User.objects.create_user(username='alice', password='secret123')
    project = Project.objects.create(name='Crumby')
    Task.objects.create(description='Filter target', project=project, status=Task.STATUS_DONE)
    Task.objects.create(description='Other task', project=project, status=Task.STATUS_TODO)

    _login(page, live_server, 'alice', 'secret123')

    page.locator('select[name="status"]').select_option('done')
    page.get_by_role('button', name='Search').click()

    page.get_by_role('link', name='Filter target').click()
    expect(page.locator('.breadcrumb')).to_be_visible()

    page.locator('.breadcrumb').get_by_role('link', name='Tasks').click()

    expect(page).to_have_url(re.compile(r'status=done'))
    expect(page.locator('table')).to_contain_text('Filter target')
    expect(page.locator('table')).not_to_contain_text('Other task')


@pytest.mark.django_db(transaction=True)
def test_task_board_view_switch_and_filter(page, live_server):
    User.objects.create_user(username='alice', password='secret123')
    project_a = Project.objects.create(name='Project A')
    project_b = Project.objects.create(name='Project B')
    Task.objects.create(description='A-todo task', project=project_a, status=Task.STATUS_TODO)
    Task.objects.create(description='A-done task', project=project_a, status=Task.STATUS_DONE)
    Task.objects.create(description='B-todo task', project=project_b, status=Task.STATUS_TODO)
    Task.objects.create(description='B-progress task', project=project_b, status=Task.STATUS_IN_PROGRESS)

    _login(page, live_server, 'alice', 'secret123')

    page.goto(f'{live_server.url}/')
    expect(page.locator('table')).to_contain_text('A-todo task')
    expect(page.locator('table')).to_contain_text('A-done task')
    expect(page.locator('table')).to_contain_text('B-todo task')
    expect(page.locator('table')).to_contain_text('B-progress task')

    page.get_by_role('tab', name='Board').click()
    expect(page).to_have_url(re.compile(r'/board/'))
    expect(page.locator('.kanban .tag--todo')).to_have_text('To do')
    expect(page.locator('.kanban .tag--in_progress')).to_have_text('In progress')
    expect(page.locator('.kanban .tag--done')).to_have_text('Done')
    expect(page.locator('.kanban')).to_contain_text('A-todo task')
    expect(page.locator('.kanban')).to_contain_text('A-done task')
    expect(page.locator('.kanban')).to_contain_text('B-todo task')
    expect(page.locator('.kanban')).to_contain_text('B-progress task')

    page.locator('select[name="project"]').select_option(label='Project A')
    page.get_by_role('button', name='Search').click()

    expect(page.locator('.kanban')).to_contain_text('A-todo task')
    expect(page.locator('.kanban')).to_contain_text('A-done task')
    expect(page.locator('.kanban')).not_to_contain_text('B-todo task')
    expect(page.locator('.kanban')).not_to_contain_text('B-progress task')

    page.get_by_role('tab', name='List').click()
    expect(page).to_have_url(re.compile(rf'project={project_a.pk}\b'))
    expect(page.locator('table')).to_contain_text('A-todo task')
    expect(page.locator('table')).to_contain_text('A-done task')
    expect(page.locator('table')).not_to_contain_text('B-todo task')
    expect(page.locator('table')).not_to_contain_text('B-progress task')
