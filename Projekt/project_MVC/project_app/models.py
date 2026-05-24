from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class Project(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('project_detail', args=[self.pk])


class Task(models.Model):
    STATUS_TODO = 'todo'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_CHOICES = [
        (STATUS_TODO, 'To do'),
        (STATUS_IN_PROGRESS, 'In progress'),
        (STATUS_DONE, 'Done'),
    ]

    description = models.CharField(max_length=300)
    details = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.description

    def get_absolute_url(self):
        return reverse('task_detail', args=[self.pk])

    @property
    def is_overdue(self) -> bool:
        return (
            self.deadline is not None
            and self.deadline < timezone.localdate()
            and self.status != self.STATUS_DONE
        )


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='comments',
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment on {self.task_id} by {self.author_id}"


class Team(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='TeamMembership',
        related_name='teams',
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('team_detail', args=[self.pk])

    def membership_for(self, user):
        if not user.is_authenticated:
            return None
        return self.memberships.filter(user=user).first()

    def is_manager(self, user):
        membership = self.membership_for(user)
        return membership is not None and membership.role == TeamMembership.ROLE_MANAGER

    def has_member(self, user):
        return self.membership_for(user) is not None


class TeamMembership(models.Model):
    ROLE_MEMBER = 'member'
    ROLE_MANAGER = 'manager'
    ROLE_CHOICES = [
        (ROLE_MEMBER, 'Member'),
        (ROLE_MANAGER, 'Manager'),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='team_memberships',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('team', 'user')]
        ordering = ['team', 'user']

    def __str__(self):
        return f"{self.user} in {self.team} ({self.role})"
