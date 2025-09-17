# Testimonials API Documentation

## Overview

The Testimonials API provides comprehensive endpoints for managing customer testimonials, including creation, moderation, categorization, and media management. The API follows RESTful principles and includes role-based access control for different user types.

## Base URL

All API endpoints are prefixed with `/testimonials/api/`

## Authentication & Permissions

The API supports different permission levels:
- **Anonymous Users**: Can view published testimonials and create new ones
- **Authenticated Users**: Can view their own testimonials + published ones, create testimonials
- **Authors**: Can edit/delete their own testimonials
- **Moderators**: Can approve, reject, feature, and archive testimonials
- **Admins**: Full access to all functionality

## Response Format

All responses follow a consistent JSON format:

```json
{
  "count": 25,
  "next": "http://example.com/testimonials/api/testimonials/?page=2",
  "previous": null,
  "results": [...]
}
```

## Error Responses

```json
{
  "detail": "Error message",
  "field_errors": {
    "field_name": ["Error message"]
  }
}
```

---

# Testimonial Endpoints

## 1. List Testimonials

**GET** `/testimonials/`

Retrieve a paginated list of testimonials.

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `page_size` | integer | Items per page (max 100) |
| `search` | string | Search in author_name, company, content, title |
| `category` | integer | Filter by category ID |
| `rating` | integer | Filter by rating |
| `status` | string | Filter by status (admin/moderator only) |
| `ordering` | string | Sort by: `created_at`, `rating`, `display_order`, `-created_at`, etc. |

### Response

```json
{
  "count": 15,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "author_name": "John Doe",
      "author_email": "john@example.com",
      "author_phone": "+1234567890",
      "author_title": "CEO",
      "company": "Example Corp",
      "location": "New York, NY",
      "avatar": "/media/avatars/john.jpg",
      "title": "Great service!",
      "content": "This product exceeded my expectations...",
      "rating": 5,
      "category": {
        "id": 1,
        "name": "Product Reviews",
        "slug": "product-reviews",
        "description": "Customer feedback on our products"
      },
      "source": "website",
      "source_display": "Website",
      "status": "approved",
      "status_display": "Approved",
      "is_anonymous": false,
      "is_verified": true,
      "media": [
        {
          "id": 1,
          "file": "/media/testimonials/image.jpg",
          "file_url": "/media/testimonials/image.jpg",
          "media_type": "image",
          "media_type_display": "Image",
          "title": "Product Screenshot",
          "description": "Screenshot showing the product in use",
          "is_primary": true,
          "order": 1,
          "created_at": "2024-01-15T10:30:00Z"
        }
      ],
      "display_order": 10,
      "slug": "great-service-john-doe",
      "website": "https://example.com",
      "social_media": {
        "linkedin": "https://linkedin.com/in/johndoe",
        "twitter": "@johndoe"
      },
      "response": "Thank you for your feedback!",
      "created_at": "2024-01-15T10:00:00Z",
      "updated_at": "2024-01-15T11:00:00Z",
      "approved_at": "2024-01-15T10:45:00Z"
    }
  ]
}
```

---

## 2. Create Testimonial

**POST** `/testimonials/`

Create a new testimonial.

### Request Body

```json
{
  "author_name": "Jane Smith",
  "author_email": "jane@example.com",
  "author_phone": "+1987654321",
  "author_title": "Marketing Director",
  "company": "Tech Solutions Inc",
  "location": "San Francisco, CA",
  "avatar": null,
  "title": "Excellent Product",
  "content": "I've been using this product for 6 months and it has significantly improved our workflow...",
  "rating": 5,
  "category_id": 1,
  "is_anonymous": false,
  "website": "https://techsolutions.com",
  "social_media": {
    "linkedin": "https://linkedin.com/in/janesmith"
  }
}
```

### Response

**201 Created**

Returns the created testimonial object with all fields populated.

### Validation Rules

- `rating`: Required, must be between 1 and maximum rating (configured in settings)
- `author_name`: Required unless is_anonymous is true. If not provided for authenticated users, will be auto-filled from the user's full name or username
- `content`: Required
- `is_anonymous`: If true and anonymous testimonials are disabled, will return validation error

---

## 3. Retrieve Testimonial

**GET** `/testimonials/{id}/`

Retrieve a specific testimonial by ID.

### Response

Returns detailed testimonial object including additional fields:

```json
{
  "id": 1,
  // ... all fields from list view plus:
  "ip_address": "192.168.1.1",
  "rejection_reason": null,
  "extra_data": {},
  "response_at": "2024-01-15T11:00:00Z",
  "approved_by": 2
}
```

---

## 4. Update Testimonial

**PUT** `/testimonials/{id}/` or **PATCH** `/testimonials/{id}/`

Update a testimonial. Only available to the author or admins.

### Request Body

Same as create, but all fields are optional for PATCH requests.

### Response

**200 OK** - Returns updated testimonial object

---

## 5. Delete Testimonial

**DELETE** `/testimonials/{id}/`

Delete a testimonial. Only available to the author or admins.

### Response

**204 No Content**

---

# Custom Testimonial Actions

## 6. My Testimonials

**GET** `/testimonials/mine/`

Retrieve testimonials created by the current authenticated user.

### Authentication Required

Yes - Returns 401 if not authenticated.

### Response

Same format as list testimonials, but filtered to current user's testimonials only.

---

## 7. Pending Testimonials

**GET** `/testimonials/pending/`

Retrieve testimonials with pending status. Moderator/admin only.

### Permissions Required

User must be a moderator or admin.

### Response

Same format as list testimonials, but filtered to pending testimonials only.

---

## 8. Approve Testimonial

**POST** `/testimonials/{id}/approve/`

Approve a pending testimonial. Moderator/admin only.

### Permissions Required

User must be a moderator or admin.

### Response

**200 OK**

```json
{
  "id": 1,
  // Updated testimonial object with status changed to "approved"
  "status": "approved",
  "approved_at": "2024-01-15T12:00:00Z",
  "approved_by": 2
}
```

### Error Responses

- **400 Bad Request**: If testimonial is already approved
- **403 Forbidden**: If user lacks permissions
- **404 Not Found**: If testimonial doesn't exist

---

## 9. Reject Testimonial

**POST** `/testimonials/{id}/reject/`

Reject a testimonial with a reason. Moderator/admin only.

### Request Body

```json
{
  "rejection_reason": "Content does not meet our guidelines"
}
```

### Permissions Required

User must be a moderator or admin.

### Response

**200 OK** - Returns updated testimonial object with status changed to "rejected"

### Validation

- `rejection_reason` is required

---

## 10. Feature Testimonial

**POST** `/testimonials/{id}/feature/`

Mark a testimonial as featured. Moderator/admin only.

### Permissions Required

User must be a moderator or admin.

### Response

**200 OK** - Returns updated testimonial object with status changed to "featured"

---

## 11. Archive Testimonial

**POST** `/testimonials/{id}/archive/`

Archive a testimonial. Moderator/admin only.

### Permissions Required

User must be a moderator or admin.

### Response

**200 OK** - Returns updated testimonial object with status changed to "archived"

---

## 12. Add Response

**POST** `/testimonials/{id}/respond/`

Add a response to a testimonial.

### Request Body

```json
{
  "response": "Thank you for your valuable feedback! We're glad to hear about your positive experience."
}
```

### Response

**200 OK** - Returns updated testimonial object with response added

### Validation

- `response` is required and cannot be empty

---

## 13. Add Media

**POST** `/testimonials/{id}/add_media/`

Add media (image, video, etc.) to a testimonial.

### Request Body

Form data:
- `file`: The media file to upload
- `title`: Optional title for the media
- `description`: Optional description

### Response

**201 Created**

```json
{
  "id": 5,
  "file": "/media/testimonials/video.mp4",
  "file_url": "/media/testimonials/video.mp4",
  "media_type": "video",
  "media_type_display": "Video",
  "title": "Product Demo",
  "description": "Customer showing product in action",
  "is_primary": false,
  "order": 2,
  "created_at": "2024-01-15T13:00:00Z"
}
```

---

## 14. Bulk Moderate

**POST** `/testimonials/moderate/`

Perform bulk actions on multiple testimonials. Moderator/admin only.

### Request Body

```json
{
  "action": "approve",
  "testimonial_ids": [1, 2, 3, 4],
  "rejection_reason": "Optional reason for bulk rejection"
}
```

### Actions Available

- `approve`: Approve selected testimonials
- `reject`: Reject selected testimonials (requires `rejection_reason`)
- `feature`: Feature selected testimonials
- `archive`: Archive selected testimonials

### Response

**200 OK**

```json
{
  "detail": "Successfully moderated 4 testimonials.",
  "count": 4
}
```

---

# Category Endpoints

## 15. List Categories

**GET** `/categories/`

Retrieve all testimonial categories.

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search in name and description |
| `ordering` | string | Sort by: `name`, `order`, `-name`, `-order` |

### Response

```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Product Reviews",
      "slug": "product-reviews",
      "description": "Customer feedback on our products",
      "is_active": true,
      "order": 1,
      "testimonials_count": 25,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

---

## 16. Create Category

**POST** `/categories/`

Create a new testimonial category. Admin only.

### Request Body

```json
{
  "name": "Service Reviews",
  "description": "Customer feedback on our services",
  "is_active": true,
  "order": 2
}
```

### Response

**201 Created** - Returns created category object

---

## 17. Retrieve Category

**GET** `/categories/{id}/`

Retrieve a specific category by ID.

---

## 18. Update Category

**PUT** `/categories/{id}/` or **PATCH** `/categories/{id}/`

Update a category. Admin only.

---

## 19. Delete Category

**DELETE** `/categories/{id}/`

Delete a category. Admin only.

---

## 20. Category Testimonials

**GET** `/categories/{id}/testimonials/`

Retrieve all testimonials for a specific category.

### Response

Same format as testimonial list, filtered by category.

---

# Media Endpoints

## 21. List Media

**GET** `/media/`

Retrieve testimonial media files.

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `testimonial` | integer | Filter by testimonial ID |
| `media_type` | string | Filter by media type |
| `is_primary` | boolean | Filter by primary media |
| `ordering` | string | Sort by: `order`, `created_at`, `-order`, `-created_at` |

### Response

```json
{
  "count": 10,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "file": "/media/testimonials/image.jpg",
      "file_url": "/media/testimonials/image.jpg",
      "media_type": "image",
      "media_type_display": "Image",
      "title": "Product Screenshot",
      "description": "Customer's product setup",
      "is_primary": true,
      "order": 1,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

---

## 22. Create Media

**POST** `/media/`

Upload new media file.

### Request Body

Form data:
- `file`: Media file
- `testimonial`: Testimonial ID
- `title`: Optional title
- `description`: Optional description
- `is_primary`: Boolean, default false
- `order`: Integer, default 0

---

## 23. Retrieve Media

**GET** `/media/{id}/`

Retrieve specific media file details.

---

## 24. Update Media

**PUT** `/media/{id}/` or **PATCH** `/media/{id}/`

Update media metadata. Author or admin only.

---

## 25. Delete Media

**DELETE** `/media/{id}/`

Delete media file. Author or admin only.

---

## 26. Media by Testimonial

**GET** `/media/by_testimonial/?testimonial_id={id}`

Retrieve all media files for a specific testimonial.

### Query Parameters

- `testimonial_id`: Required - ID of the testimonial

### Response

Same format as media list, filtered by testimonial.

---

# Status Codes

## Success Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **204 No Content**: Resource deleted successfully

## Error Codes

- **400 Bad Request**: Invalid request data or validation errors
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **405 Method Not Allowed**: HTTP method not supported for endpoint

---

# Rate Limiting

The API implements standard pagination with a default page size configured in settings. Maximum page size is limited to 100 items per request.

---

# Filtering & Search

Most list endpoints support:

- **Search**: Full-text search across relevant fields
- **Filtering**: Filter by specific field values
- **Ordering**: Sort by various fields (ascending/descending)

Use query parameters to combine multiple filters and searches.

---

# Media Types Supported

The API supports various media types for testimonial attachments:
- Images (JPEG, PNG, GIF, WebP)
- Videos (MP4, WebM, AVI)
- Audio files (MP3, WAV, OGG)
- Documents (PDF, DOC, DOCX)

File size and type restrictions are configured in the application settings.