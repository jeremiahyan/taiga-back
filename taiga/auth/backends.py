# -*- coding: utf-8 -*-
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2021-present Kaleidos Ventures SL

"""
Authentication backends for rest framework.

This module exposes two backends: session and token.

The first (session) is a modified version of standard
session authentication backend of restframework with
csrf token disabled.

And the second (token) implements own version of oauth2
like authentication but with selfcontained tokens. Thats
makes authentication totally stateless.

It uses django signing framework for create new
self-contained tokens. This trust tokes from external
fraudulent modifications.
"""

import re

from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from taiga.base.api.authentication import BaseAuthentication

from .tokens import get_user_for_token


class Session(BaseAuthentication):
    """
    Session based authentication like the standard
    `taiga.base.api.authentication.SessionAuthentication`
    but with csrf disabled (for obvious reasons because
    it is for api.

    NOTE: this is only for api web interface. Is not used
    for common api usage and should be disabled on production.
    """

    def authenticate(self, request):
        http_request = request._request
        user = getattr(http_request, 'user', None)

        if not user or not user.is_active:
            return None

        return (user, None)


class Token(BaseAuthentication):
    """
    Self-contained stateless authentication implementation
    that works similar to oauth2.
    It uses django signing framework for trust data stored
    in the token.
    """

    auth_rx = re.compile(r"^Bearer (.+)$")

    def authenticate(self, request):
        if "HTTP_AUTHORIZATION" not in request.META:
            return None

        token_rx_match = self.auth_rx.search(request.META["HTTP_AUTHORIZATION"])
        if not token_rx_match:
            return None

        token = token_rx_match.group(1)
        max_age_auth_token = getattr(settings, "MAX_AGE_AUTH_TOKEN", None)
        user = get_user_for_token(token, "authentication",
                                  max_age=max_age_auth_token)

        if user.last_login is None or user.last_login < (timezone.now() - timedelta(minutes=1)):
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

        return (user, token)

    def authenticate_header(self, request):
        return 'Bearer realm="api"'
