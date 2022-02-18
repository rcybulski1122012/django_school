from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from django_school.apps.classes.models import Class
from django_school.apps.messages.forms import MessageForm
from django_school.apps.messages.models import Message

User = get_user_model()


class MessagesListView(LoginRequiredMixin, ListView):
    model = Message
    ordering = ["-created"]
    paginate_by = 10
    context_object_name = "school_messages"

    def get_queryset(self):
        return super().get_queryset().select_related("sender")


class ReceivedMessagesListView(MessagesListView):
    template_name = "messages/received_list.html"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .received(self.request.user)
            .with_statuses(receiver=self.request.user)
        )


class SentMessagesListView(MessagesListView):
    template_name = "messages/sent_list.html"

    def get_queryset(self):
        return super().get_queryset().sent(self.request.user)


class MessageCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = "messages/message_form.html"
    success_url = reverse_lazy("messages:sent")
    success_message = "The message has been sent successfully"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teachers = User.teachers.all()
        classes = Class.objects.prefetch_related("students__parent")

        context.update(
            {
                "teachers": teachers,
                "classes": classes,
            }
        )

        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["sender"] = self.request.user

        return kwargs


class MessageDetailView(LoginRequiredMixin, DetailView):
    model = Message
    pk_url_kwarg = "message_pk"
    template_name = "messages/message_detail.html"
    context_object_name = "school_message"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(Q(sender=self.request.user) | Q(receivers=self.request.user))
            .select_related("sender")
            .with_statuses(receiver=self.request.user)
            .distinct()
        )

    def get(self, request, *args, **kwargs):
        result = super().get(request, *args, **kwargs)

        if self.object.status:
            status = self.object.status[0]
            if not status.is_read:
                status.is_read = True
                status.save()

        return result
