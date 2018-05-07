from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.contrib.auth.models import User
from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist
from TALK_app.forms import AuthenticateForm, UserCreateForm, TALKForm
from TALK_app.models import TALK


def index(request, auth_form=None, user_form=None):
    # User is logged in
    if request.user.is_authenticated:
        TALK_form = TALKForm()
        user = request.user
        TALKs_self = TALK.objects.filter(user=user.id)
        TALKs_buddies = TALK.objects.filter(user__userprofile__in=user.profile.follows.all())
        TALKs = TALKs_self | TALKs_buddies

        return render(request,
                      'buddies.html',
                      {'TALK_form': TALK_form, 'user': user,
                       'TALKs': TALKs,
                       'next_url': '/', })
    else:
        # User is not logged in
        auth_form = auth_form or AuthenticateForm()
        user_form = user_form or UserCreateForm()

        return render(request,
                      'home.html',
                      {'auth_form': auth_form, 'user_form': user_form, })


def login_view(request):
    if request.method == 'POST':
        form = AuthenticateForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            # Success
            return redirect('/')
        else:
            # Failure
            return index(request, auth_form=form)
    return redirect('/')


def logout_view(request):
    logout(request)
    return redirect('/')


def signup(request):
    user_form = UserCreateForm(data=request.POST)
    if request.method == 'POST':
        if user_form.is_valid():
            username = request.POST['username']
            password = request.POST['password1']
            user_form.save()
            user = authenticate(username=username, password=password)
            login(request, user)
            return redirect('/')
        else:
            return index(request, user_form=user_form)
    return redirect('/')


@login_required
def public(request, TALK_form=None):
    TALK_form = TALK_form or TALKForm()
    TALKs = TALK.objects.reverse()[:10]
    return render(request,
                  'public.html',
                  {'TALK_form': TALK_form, 'next_url': '/TALKs',
                   'TALKs': TALKs, 'username': request.user.username})


@login_required
def submit(request):
    if request.method == "POST":
        TALK_form = TALKForm(data=request.POST)
        next_url = request.POST.get("next_url", "/")
        if TALK_form.is_valid():
            TALK = TALK_form.save(commit=False)
            TALK.user = request.user
            TALK.save()
            return redirect(next_url)
        else:
            return public(request, TALK_form)
    return redirect('/')


def get_latest(user):
    try:
        return user.talk_set.order_by('id').reverse()[0]
    except IndexError:
        return ""


@login_required
def users(request, username="", TALK_form=None):
    if username:
        # Show a profile
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise Http404
        TALKs = TALK.objects.filter(user=user.id)
        if username == request.user.username or request.user.profile.follows.filter(user__username=username):
            # Self Profile
            return render(request, 'user.html', {'user': user, 'TALKs': TALKs, })
        return render(request, 'user.html', {'user': user, 'TALKs': TALKs, 'follow': True, })
    users = User.objects.all().annotate(TALK_count=Count('talk'))
    TALKs = map(get_latest, users)
    obj = zip(users, TALKs)
    TALK_form = TALK_form or TALKForm()
    return render(request,
                  'profiles.html',
                  {'obj': obj, 'next_url': '/users/',
                   'TALK_form': TALK_form,
                   'username': request.user.username, })


@login_required
def follow(request):
    if request.method == "POST":
        follow_id = request.POST.get('follow', False)
        if follow_id:
            try:
                user = User.objects.get(id=follow_id)
                request.user.profile.follows.add(user.profile)
            except ObjectDoesNotExist:
                return redirect('/users/')
    return redirect('/users/')
