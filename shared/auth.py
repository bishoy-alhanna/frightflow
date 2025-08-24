"""
OIDC authentication middleware with role-based access control.
Ready for Keycloak integration.
"""
import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from functools import wraps
from flask import request, jsonify, g, current_app
import requests

logger = logging.getLogger(__name__)


class AuthConfig:
    """Authentication configuration."""
    
    def __init__(self):
        self.enabled = False
        self.oidc_issuer = None
        self.oidc_audience = None
        self.oidc_client_id = None
        self.oidc_client_secret = None
        self.jwks_uri = None
        self.public_key = None
        self.algorithm = 'RS256'
        self.token_cache_ttl = 300  # 5 minutes


class User:
    """User representation with roles and permissions."""
    
    def __init__(self, user_id: str, username: str, email: str, 
                 roles: List[str], permissions: List[str], claims: Dict[str, Any]):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles
        self.permissions = permissions
        self.claims = claims
        self.is_authenticated = True
    
    def has_role(self, role: str) -> bool:
        """Check if user has specific role."""
        return role in self.roles
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if user has any of the specified roles."""
        return any(role in self.roles for role in roles)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'email': self.email,
            'roles': self.roles,
            'permissions': self.permissions,
            'is_authenticated': self.is_authenticated
        }


class AuthManager:
    """Authentication and authorization manager."""
    
    def __init__(self):
        self.config = AuthConfig()
        self._jwks_cache = {}
        self._jwks_cache_time = None
    
    def init_app(self, app):
        """Initialize auth manager with Flask app."""
        self.config.enabled = app.config.get('AUTH_ENABLED', False)
        self.config.oidc_issuer = app.config.get('OIDC_ISSUER')
        self.config.oidc_audience = app.config.get('OIDC_AUDIENCE')
        self.config.oidc_client_id = app.config.get('OIDC_CLIENT_ID')
        self.config.oidc_client_secret = app.config.get('OIDC_CLIENT_SECRET')
        self.config.jwks_uri = app.config.get('OIDC_JWKS_URI')
        self.config.public_key = app.config.get('JWT_PUBLIC_KEY')
        self.config.algorithm = app.config.get('JWT_ALGORITHM', 'RS256')
        
        if self.config.enabled:
            logger.info("Authentication enabled")
        else:
            logger.info("Authentication disabled - development mode")
    
    def _get_jwks(self) -> Dict[str, Any]:
        """Get JWKS from OIDC provider with caching."""
        now = datetime.utcnow()
        
        # Check cache
        if (self._jwks_cache and self._jwks_cache_time and 
            (now - self._jwks_cache_time).seconds < self.config.token_cache_ttl):
            return self._jwks_cache
        
        # Fetch JWKS
        if self.config.jwks_uri:
            try:
                response = requests.get(self.config.jwks_uri, timeout=10)
                response.raise_for_status()
                self._jwks_cache = response.json()
                self._jwks_cache_time = now
                return self._jwks_cache
            except Exception as e:
                logger.error(f"Failed to fetch JWKS: {e}")
        
        return {}
    
    def _get_public_key(self, token_header: Dict[str, Any]) -> Optional[str]:
        """Get public key for token verification."""
        if self.config.public_key:
            return self.config.public_key
        
        # Get key from JWKS
        kid = token_header.get('kid')
        if not kid:
            return None
        
        jwks = self._get_jwks()
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                # Convert JWK to PEM format (simplified)
                # In production, use a proper JWK to PEM converter
                return key.get('x5c', [None])[0] if key.get('x5c') else None
        
        return None
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return claims."""
        try:
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            
            # Get public key
            public_key = self._get_public_key(header)
            if not public_key:
                logger.error("No public key found for token verification")
                return None
            
            # Verify token
            claims = jwt.decode(
                token,
                public_key,
                algorithms=[self.config.algorithm],
                audience=self.config.oidc_audience,
                issuer=self.config.oidc_issuer
            )
            
            return claims
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    def create_user_from_claims(self, claims: Dict[str, Any]) -> User:
        """Create User object from JWT claims."""
        user_id = claims.get('sub', 'unknown')
        username = claims.get('preferred_username', claims.get('name', 'unknown'))
        email = claims.get('email', '')
        
        # Extract roles from claims
        roles = []
        if 'realm_access' in claims:
            roles.extend(claims['realm_access'].get('roles', []))
        if 'resource_access' in claims:
            for client, access in claims['resource_access'].items():
                roles.extend(access.get('roles', []))
        
        # Map roles to permissions (simplified mapping)
        permissions = self._map_roles_to_permissions(roles)
        
        return User(user_id, username, email, roles, permissions, claims)
    
    def _map_roles_to_permissions(self, roles: List[str]) -> List[str]:
        """Map roles to permissions."""
        role_permission_map = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'manage_system'],
            'ops': ['read', 'write', 'manage_shipments', 'manage_vendors'],
            'sales': ['read', 'write', 'manage_quotes', 'manage_customers'],
            'customer': ['read', 'view_own_data'],
            'viewer': ['read']
        }
        
        permissions = set()
        for role in roles:
            permissions.update(role_permission_map.get(role, []))
        
        return list(permissions)
    
    def authenticate_request(self) -> Optional[User]:
        """Authenticate current request and return user."""
        if not self.config.enabled:
            # Development mode - create mock user
            return User(
                user_id='dev-user',
                username='developer',
                email='dev@example.com',
                roles=['admin'],
                permissions=['read', 'write', 'delete', 'manage_users', 'manage_system'],
                claims={'sub': 'dev-user', 'preferred_username': 'developer'}
            )
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Verify token
        claims = self.verify_token(token)
        if not claims:
            return None
        
        # Create user from claims
        return self.create_user_from_claims(claims)


# Global auth manager instance
auth_manager = AuthManager()


def init_auth(app):
    """Initialize authentication with Flask app."""
    auth_manager.init_app(app)
    
    @app.before_request
    def authenticate_request():
        """Authenticate request and set current user."""
        g.current_user = auth_manager.authenticate_request()


def require_auth(f: Callable) -> Callable:
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not g.get('current_user'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_role(role: str) -> Callable:
    """Decorator to require specific role."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = g.get('current_user')
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            
            if not user.has_role(role):
                return jsonify({'error': f'Role {role} required'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_any_role(roles: List[str]) -> Callable:
    """Decorator to require any of the specified roles."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = g.get('current_user')
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            
            if not user.has_any_role(roles):
                return jsonify({'error': f'One of roles {roles} required'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(permission: str) -> Callable:
    """Decorator to require specific permission."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = g.get('current_user')
            if not user:
                return jsonify({'error': 'Authentication required'}), 401
            
            if not user.has_permission(permission):
                return jsonify({'error': f'Permission {permission} required'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_current_user() -> Optional[User]:
    """Get current authenticated user."""
    return g.get('current_user')


def is_authenticated() -> bool:
    """Check if current request is authenticated."""
    user = get_current_user()
    return user is not None and user.is_authenticated

