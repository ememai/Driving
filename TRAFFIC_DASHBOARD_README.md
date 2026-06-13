# Traffic Dashboard Implementation Guide

## Overview

A complete website traffic analytics dashboard has been built for your Django application. It tracks all HTTP requests, user visits, and provides comprehensive analytics with visualizations.

## What Was Built

### 1. **TrafficLog Model** (`app/models.py`)

- Tracks all HTTP requests to the website
- Records user, IP address, path, HTTP method, status code, response time, referrer, and user agent
- Automatically creates database indexes for efficient querying
- Fields:
  - `user`: FK to UserProfile (null if anonymous)
  - `path`: Request path
  - `method`: HTTP method (GET, POST, etc.)
  - `status_code`: HTTP response code
  - `ip_address`: Client IP address
  - `user_agent`: Browser/client information
  - `referrer`: Source of the request
  - `response_time`: Response time in milliseconds
  - `timestamp`: When the request was made

### 2. **Traffic Logging Middleware** (`app/middleware.py`)

- **TrafficLoggingMiddleware**: Automatically logs all HTTP traffic
- Calculates response time for each request
- Skips logging for static files and media to reduce noise
- Gets client IP address handling proxies correctly
- Silently fails to avoid breaking the application if database is unavailable

### 3. **Traffic Dashboard View** (`dashboard/views.py`)

- **traffic_dashboard()**: Protected staff-only view
- Provides multiple time range filters (24h, 7d, 30d, 90d)
- Generates real-time analytics including:
  - Total requests
  - Unique users
  - Unique IP addresses
  - Average response time
  - Top pages by traffic
  - HTTP status code distribution
  - Hourly traffic patterns
  - Top referrers
  - HTTP methods breakdown
  - Paginated recent traffic logs

### 4. **Traffic Dashboard Template** (`dashboard/templates/dashboard/traffic_dashboard.html`)

- Modern, responsive design with Bootstrap 5
- Key statistics displayed in gradient cards
- Hourly traffic visualization using Chart.js
- Tables showing:
  - Top pages
  - HTTP status codes with color-coded badges
  - HTTP methods
  - Top referrers
  - Recent traffic logs (paginated)
- Time range filters for quick analysis
- Color-coded status codes (200=green, 400=yellow, 500=red, etc.)

### 5. **Admin Integration** (`app/admin.py`)

- TrafficLog registered in Django admin
- Staff can view traffic data in the admin panel
- Read-only fields to prevent accidental modifications
- Filterable by timestamp, status code, and method
- Searchable by path, IP, and username

### 6. **Navigation Update** (`dashboard/templates/dashboard/base.html`)

- Added "Traffic Analytics" link to dashboard navbar
- Easy access to the traffic dashboard from anywhere in the admin panel

## How It Works

### Automatic Traffic Logging

1. Every HTTP request passes through **TrafficLoggingMiddleware**
2. Middleware captures request data and calculates response time
3. After response is sent, a `TrafficLog` entry is created
4. Static files and media are excluded to reduce database bloat

### Accessing the Dashboard

**URL**: `/dashboard/traffic/`

**Requirements**:

- User must be logged in
- User must have staff privileges (`is_staff = True`)

**Navigation**:

1. Login to admin dashboard
2. Click "Traffic Analytics" in the navbar
3. Select time range (24h, 7d, 30d, 90d)
4. View analytics and insights

## Features

### Analytics Provided

- **Total Requests**: Total HTTP requests in the selected period
- **Unique Users**: Number of logged-in users
- **Unique IPs**: Number of unique IP addresses
- **Average Response Time**: Mean response time in milliseconds
- **Top Pages**: Most visited pages/paths
- **Status Codes**: Distribution of HTTP response codes
- **Hourly Traffic**: Traffic pattern over the last 24 hours (line chart)
- **HTTP Methods**: Breakdown of GET, POST, PUT, DELETE requests
- **Top Referrers**: Where traffic is coming from
- **Recent Logs**: Paginated view of recent traffic (50 per page)

### Filters & Controls

- **Time Range Buttons**: 24h, 7d, 30d, 90d quick filters
- **Pagination**: Navigate through recent traffic logs
- **Status Code Colors**:
  - Green (2xx): Successful requests
  - Blue (3xx): Redirects
  - Yellow (4xx): Client errors
  - Red (5xx): Server errors

## Database Optimization

The TrafficLog model includes indexes on:

- `-timestamp`: For fast sorting
- `path, -timestamp`: For page-specific analytics
- `user, -timestamp`: For user-specific analytics
- `status_code, -timestamp`: For error analysis

This ensures fast queries even with millions of log entries.

## Configuration

### Middleware Registration

The middleware is already registered in `mwami/settings.py`:

```python
MIDDLEWARE = [
    ...
    'app.middleware.TrafficLoggingMiddleware',
]
```

### Skipped Paths

The following paths are NOT logged:

- `/static/*`: Static files
- `/media/*`: Media files
- `/favicon.ico`: Favicon
- `/.well-known/*`: Well-known paths

### Customization

To add more excluded paths, edit `app/middleware.py`:

```python
skip_paths = ['/static/', '/media/', '/favicon.ico', '/.well-known/']
```

## Performance Considerations

1. **Non-blocking**: Logging happens after response is sent
2. **Graceful Failures**: If logging fails, the user request is unaffected
3. **Database Indexes**: Queries are optimized with proper indexes
4. **Pagination**: Recent logs are paginated (50 per page) for performance
5. **Exclusions**: Static/media files are excluded to reduce noise

## Admin Panel Integration

In Django Admin (`/admin/app/trafficlog/`):

- View all traffic logs
- Filter by timestamp, status code, HTTP method
- Search by path, IP address, username
- Read-only interface (no accidental modifications)
- Only superusers can delete logs

## API Response Time Tracking

The middleware automatically calculates and stores response time in milliseconds:

- Fast responses: < 50ms
- Normal responses: 50-500ms
- Slow responses: > 500ms
- Very slow responses: > 2000ms

Use this metric to identify performance bottlenecks in your application.

## Troubleshooting

### No Traffic Data Appearing

1. Check that middleware is enabled in settings.py
2. Verify `app.middleware.TrafficLoggingMiddleware` is in MIDDLEWARE list
3. Make sure migrations were applied: `python manage.py migrate`
4. Check database connectivity

### Database Growing Too Large

- Monitor TrafficLog table size
- Consider archiving old logs periodically:

  ```python
  from datetime import timedelta
  from django.utils import timezone
  from app.models import TrafficLog

  old_logs = TrafficLog.objects.filter(
      timestamp__lt=timezone.now() - timedelta(days=90)
  )
  old_logs.delete()
  ```

### Middleware Not Logging

1. Verify it's listed in MIDDLEWARE (correct path: `app.middleware.TrafficLoggingMiddleware`)
2. Check for import errors: `python manage.py check`
3. Enable DEBUG mode to see middleware execution

## Next Steps

1. **Visit the dashboard**: Navigate to `/dashboard/traffic/`
2. **Monitor traffic patterns**: Check peak hours and popular pages
3. **Identify issues**: Look for 500 errors and slow responses
4. **Optimize**: Use insights to improve application performance
5. **Archive logs**: Periodically clean up old logs to save space

## Files Modified/Created

- `app/models.py` - Added TrafficLog model
- `app/middleware.py` - Added TrafficLoggingMiddleware
- `dashboard/views.py` - Added traffic_dashboard view
- `dashboard/urls.py` - Added traffic dashboard URL
- `dashboard/templates/dashboard/traffic_dashboard.html` - Created new template
- `dashboard/templates/dashboard/base.html` - Added navbar link
- `mwami/settings.py` - Registered middleware
- `app/admin.py` - Registered TrafficLog in admin
- `app/migrations/0077_*` - Database migration

## Database Migration

Migration `0077_alter_contactmessage_options_trafficlog` has been applied.
TrafficLog table is now ready in the database.

---

**Status**: ✅ Complete and Ready to Use

The traffic dashboard is now fully functional and will automatically start tracking traffic on your website!
