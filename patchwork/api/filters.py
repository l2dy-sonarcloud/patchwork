# Patchwork - automated patch tracking system
# Copyright (C) 2017 Stephen Finucane <stephen@that.guru>
#
# This file is part of the Patchwork package.
#
# Patchwork is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Patchwork is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Patchwork; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django_filters import FilterSet
from django_filters import IsoDateTimeFilter
from django_filters import ModelMultipleChoiceFilter
from django.forms import ModelMultipleChoiceField as BaseMultipleChoiceField

from patchwork.models import Bundle
from patchwork.models import Check
from patchwork.models import CoverLetter
from patchwork.models import Event
from patchwork.models import Patch
from patchwork.models import Person
from patchwork.models import Project
from patchwork.models import Series
from patchwork.models import State


# custom fields, filters

class ModelMultipleChoiceField(BaseMultipleChoiceField):

    def _get_filter(self, value):
        try:
            return 'pk', int(value)
        except ValueError:
            return self.alternate_lookup, value

    def _check_values(self, value):
        """
        Given a list of possible PK values, returns a QuerySet of the
        corresponding objects. Raises a ValidationError if a given value is
        invalid (not a valid PK, not in the queryset, etc.)
        """
        # deduplicate given values to avoid creating many querysets or
        # requiring the database backend deduplicate efficiently.
        try:
            value = frozenset(value)
        except TypeError:
            # list of lists isn't hashable, for example
            raise ValidationError(
                self.error_messages['list'],
                code='list',
            )

        q_objects = Q()

        for pk in value:
            key, val = self._get_filter(pk)

            try:
                # NOTE(stephenfin): In contrast to the Django implementation
                # of this, we check to ensure each specified key exists and
                # fail if not. If we don't this, we can end up doing nothing
                # for the filtering which, to me, seems very confusing
                self.queryset.get(**{key: val})
            except (ValueError, TypeError, self.queryset.model.DoesNotExist):
                raise ValidationError(
                    self.error_messages['invalid_pk_value'],
                    code='invalid_pk_value',
                    params={'pk': val},
                )

            q_objects |= Q(**{key: val})

        qs = self.queryset.filter(q_objects)

        return qs


class ProjectChoiceField(ModelMultipleChoiceField):

    alternate_lookup = 'linkname__iexact'


class ProjectFilter(ModelMultipleChoiceFilter):

    field_class = ProjectChoiceField


class PersonChoiceField(ModelMultipleChoiceField):

    alternate_lookup = 'email__iexact'


class PersonFilter(ModelMultipleChoiceFilter):

    field_class = PersonChoiceField


class StateChoiceField(ModelMultipleChoiceField):

    def _get_filter(self, value):
        try:
            return 'pk', int(value)
        except ValueError:
            return 'name__iexact', ' '.join(value.split('-'))


class StateFilter(ModelMultipleChoiceFilter):

    field_class = StateChoiceField


class UserChoiceField(ModelMultipleChoiceField):

    alternate_lookup = 'username__iexact'


class UserFilter(ModelMultipleChoiceFilter):

    field_class = UserChoiceField


# filter sets

class TimestampMixin(FilterSet):

    # TODO(stephenfin): These should filter on a 'updated_at' field instead
    before = IsoDateTimeFilter(name='date', lookup_expr='lt')
    since = IsoDateTimeFilter(name='date', lookup_expr='gte')


class ProjectMixin(FilterSet):

    project = ProjectFilter(queryset=Project.objects.all())


class SeriesFilter(ProjectMixin, TimestampMixin, FilterSet):

    submitter = PersonFilter(queryset=Person.objects.all())

    class Meta:
        model = Series
        fields = ('submitter', 'project')


class CoverLetterFilter(ProjectMixin, TimestampMixin, FilterSet):

    submitter = PersonFilter(queryset=Person.objects.all())

    class Meta:
        model = CoverLetter
        fields = ('project', 'series', 'submitter')


class PatchFilter(ProjectMixin, TimestampMixin, FilterSet):

    submitter = PersonFilter(queryset=Person.objects.all())
    delegate = UserFilter(queryset=User.objects.all())
    state = StateFilter(queryset=State.objects.all())

    class Meta:
        model = Patch
        fields = ('project', 'series', 'submitter', 'delegate',
                  'state', 'archived')


class CheckFilter(TimestampMixin, FilterSet):

    user = UserFilter(queryset=User.objects.all())

    class Meta:
        model = Check
        fields = ('user', 'state', 'context')


class EventFilter(ProjectMixin, TimestampMixin, FilterSet):

    class Meta:
        model = Event
        fields = ('project', 'category', 'series', 'patch', 'cover')


class BundleFilter(ProjectMixin, FilterSet):

    owner = UserFilter(queryset=User.objects.all())

    class Meta:
        model = Bundle
        fields = ('project', 'owner', 'public')
