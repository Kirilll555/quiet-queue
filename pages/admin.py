from django.contrib import admin
from .models import Institution, QueueReport, InstitutionRequest

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category')
    search_fields = ('name',)

@admin.register(QueueReport)
class QueueReportAdmin(admin.ModelAdmin):
    list_display = ('institution', 'queue_level', 'created_at')
    list_filter = ('queue_level', 'institution')


@admin.register(InstitutionRequest)
class InstitutionRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'created_at', 'is_processed')
    list_filter = ('is_processed',)
    actions = ['approve_requests']

    @admin.action(description="Одобрить выбранные заявки и добавить на сайт")
    def approve_requests(self, request, queryset):
        approved_count = 0
        for req in queryset:
            if not req.is_processed:
                Institution.objects.create(
                    name=req.name,
                    category=req.category
                )
                req.is_processed = True
                req.save()
                approved_count += 1

        self.message_user(request, f"Успешно добавлено учреждений: {approved_count}")