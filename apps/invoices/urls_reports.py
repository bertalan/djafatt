from django.urls import path

from .views_reports import mark_paid, mark_unpaid, payment_form, record_payment, report_csv, report_index, report_pdf

urlpatterns = [
    path("", report_index, name="reports-index"),
    path("csv/", report_csv, name="reports-csv"),
    path("pdf/", report_pdf, name="reports-pdf"),
    path("mark-paid/<int:pk>/", mark_paid, name="reports-mark-paid"),
    path("mark-unpaid/<int:pk>/", mark_unpaid, name="reports-mark-unpaid"),
    path("payment-form/<int:pk>/", payment_form, name="reports-payment-form"),
    path("record-payment/<int:pk>/", record_payment, name="reports-record-payment"),
]
