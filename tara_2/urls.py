"""
URL configuration for tara_2 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from myapp.views import *
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('on/', turn_on, name='turn_on'),
    path('off/', turn_off, name='turn_off'),
    path('status/', check_status, name='check_status'),

    path('navigation/create/', create_navigation, name='create-navigation'),
    path('navigation/edit/<int:navigation_id>/', edit_navigation, name='edit_navigation'),

    path('navigation/list/', list_navigation, name='list-navigation'),
    path('navigation/<int:nav_id>/', get_navigation_by_id, name='get_navigation_by_id'),
    path("delete-navigation/", delete_all_navigation, name="delete_all_navigation"),
    path('navigation/last-clicked/', get_last_clicked_navigation, name='get_last_clicked_navigation'),
    path('base/status/', get_base_status, name='base_status'),
    path('update/base/status/', update_base_status, name='update_base_status'),

    path("volume/set/<str:robo_id>/<int:volume>/", set_volume, name="set_volume"),
    path("volume/get/<str:robo_id>/", get_volume, name="get_volume"),

    path("update_status/", update_status, name="update_status"),
    path("list_status/", list_status, name="list_status"),


    path('full_tour/create/', create_full_tour, name='create_full_tour'),
    path('full_tour/list/', full_tour_list, name='full_tour_list'),

    path('delete-status/', delete_status, name='update_status'),
    path('get_delete_status/', get_delete_status, name='get_status'),

    path('robot/message/post/<str:robot_id>/', post_message, name="post_message"),
    path('robot/message/get/<str:robot_id>/', get_message, name="get_message"),
    path('robot/button/clicked/<str:robot_id>/', button_click, name="button_click"),
    path('robot/button/status/<str:robot_id>/', button_status, name="button_status"),

    path('api-key/upload/', upload_api_key, name='upload-api-key'),
    path('api-key/', get_api_key, name='get-api-key'),

    path('tour/status/', get_tour_status, name='get-tour-status'),  
    path('tour/update/', update_tour_status, name='update-tour-status'),  
    
    path("update-reboot-status/", update_reboot_status, name="update_reboot_status"),
    path("get-reboot-status/", get_reboot_status, name="get_reboot_status"),

    path("update-offline-status/", update_offline_status, name="update_offline_status"),
    path("get-offline-status/", get_offline_status, name="get_offline_status"),

    path('robot-battery/', robot_battery_view, name='robot-battery'),
    path('robot-battery/list/', robot_battery_list, name='robot-battery-list'), 

    path('url/add/', create_or_replace_url, name='create-or-replace-url'),
    path('url/list/', url_list, name='url-list'),

    path('charge/update/', create_or_update_charge, name='create_or_update_charge url'),
    path('charge/current/', get_current_charge, name='get_current_charge url'),

    path('add_wishing_commands/', add_wishing_commands, name='add wishing commands url'),
   

    path('wishing/update/<int:pk>/', update_wishing_command, name='update-wishing-command'),
    path('edit_wishing_commands/', edit_description, name='edit wishing commands url'),
    path('deactivate_description/', deactivate_description, name='deactivate description url'),
    

    path('start_stop_button_press/',change_refresh_status,name='start stop button press url'),
    path('fetch_refresh_status/',fetch_refresh_status,name='fetch refresh status url'),

    path('speed/value/', update_or_create_speed, name='update_or_create_speed url'),
    path('current_speed/', get_current_speed_value, name='get_current_speed_value url'),

    

    path('charging/get/', get_charging_status, name='get-charging'),
    path('charging/set/', set_charging_status, name='set-charging'),


    path('stcm_files/create/', create_stcm_files, name='create_stcm_files'),
    path('stcm_files/<str:robot_id>/', get_stcm_files, name='get_stcm_files'),
    path('stcm_files/delete/<str:robot_id>/', delete_stcm_files, name='delete_stcm_files'),
    
    path('stcm_files/has/<str:robot_id>/', has_stcm_files , name='has delete stcm files url'),


    path('home/set/', set_home, name='home_set'),
    path('home/get/', get_home_status, name='get-home'),


    path('prompt/list/', get_prompt, name='get-prompt'),
    path('prompt/create/', create_prompt, name='create-prompt'),
    path('prompt/update/<int:pk>/', update_prompt, name='update-prompt'),
    path('prompt/delete/<int:pk>/', delete_prompt, name='delete-prompt'),


    path('qas/create/', create_prompt_qa, name='create-prompt-qa'),
    path('qas/list/<int:prompt_id>/', list_prompt_qas_by_prompt, name='list-prompt-qas-by-prompt'),
    path('qas/update/<int:pk>/', update_prompt_qa, name='update-prompt-qa'),
    path('qas/delete/<int:pk>/', delete_prompt_qa, name='delete-prompt-qa'),
    path('prompts-with-qas/', list_prompt_with_qas, name='prompts-with-qas'),

    path('teaching/status/update/', teaching_status_update, name='teaching-toggle'),
    path('get/teaching/status/', get_teaching_status, name='teaching-status'),

    path('teaching/set/', set_teaching_started, name='set_teaching_started'),
    path('teaching/started/', is_teaching_started, name='is_teaching_started'),


    path('subjects/create/', create_subject, name='create-subject'),
    path('subjects/list/', subject_list, name='subject-list'),
    path('subjects/edit/<int:pk>/', subject_edit, name='subject-edit'),
    path('subjects/detail/<int:pk>/', subject_detail, name='subject-detail'),
    path('subjects/delete/<int:pk>/', subject_delete, name='subject-delete'),

    path('upload-pdf/', upload_pdf_document, name='upload-pdf'),
    path('pdfs/list/<int:subject_id>/', list_pdfs_by_subject, name='pdf-list-by-subject'),
    path('pdfs/edit/<int:pdf_id>/', edit_pdf_document, name='edit-pdf'),
    path('pdfs/delete/<int:pdf_id>/', delete_pdf_document, name='delete-pdf'),

    path('lastmodule/', lastmodule_replace_view, name='lastmodule-replace'),
    path('lastmodule/detail/', lastmodule_list_view, name='lastmodule-list'),

    path('toggle/camera/', camera_toggle_view, name='change or view camera toggle'),

    path('person/data/', person_data_view, name='change or view person data'),
    path('update/person/data/', update_person_data_view, name='update person data'),
    path('delete/person/data/', delete_person_data_view, name='delete person data'),

    path('joystick/', joystick_view, name='joystick'),

    path('appointment/status/create_or_update/', appointment_create_or_update, name='appointment_create_or_update'),
    path('appointment/status/get/', appointment_get, name='appointment_get'),

    path('modes/create/', create_mode, name='create-mode'),
    path('list/modes/', get_modes, name='get-modes'),
    path('modes/update/<int:pk>/', update_mode, name='update-mode'),
    path('modes/delete/<int:pk>/',delete_mode, name='delete-mode'),
    path('modes/detail/<int:pk>/', detail_mode, name='detail-mode'),

    path('gestures/create/', create_gesture, name='create-gesture'),
    path('gestures/list/', list_gestures, name='gestures-list'),
    path('gestures/edit/<int:pk>/', edit_gesture, name='edit-gesture'),
    path('gestures/detail/<int:pk>/', gesture_detail, name='gesture-detail'),
    path('gestures/delete/<int:pk>/', delete_gesture, name='delete-gesture'),

    path('assign/gestures/create/', assign_gesture_to_mode, name='assign-gesture'),
    path('assign/gestures/list/', list_gesture_assignments, name='list-assignments'),
    path('assign/gestures/delete/<int:pk>/', delete_gesture_assignment, name='delete-assignment'),

    path('modes/set_last_clicked/', set_last_clicked_mode, name='set-last-clicked-mode'),
    path('modes/last_clicked/', last_clicked_mode_detail, name='last-clicked-mode'),

    path('entertainment/mode/', entertainment_view, name='entertainment'),
    path('entertainment/status/', entertainment_status, name='entertainment-status'),

    path('upload-song/', upload_song, name='upload-song'),
    path('songs/list/', list_songs, name='list-songs'),
    path('songs/edit/<int:song_id>/', edit_song, name='edit-song'),
    path('songs/detail/<int:song_id>/', song_detail, name='song-detail'),
    path('songs/delete/<int:song_id>/', delete_song, name='delete-song'),

    path('last-clicked-song/set/', set_last_clicked_song, name='set-last-clicked-song'),
    path('last-clicked-song/get/', get_last_clicked_song, name='get-last-clicked-song'),

    path('calibration/set/', set_calibration_status, name='set-calibration-status'),
    path('calibration/get/', get_calibration_status, name='get-calibration-status'),

    



    

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
