# Testimonials Admin Guide

This guide explains how to manage testimonials, categories, and media in the Django admin panel.

---

## 1. Accessing the Admin
- URL: `/admin/`  
- Log in with your admin username and password.  
- If you have a **custom dashboard** enabled via `TESTIMONIALS_ENABLE_DASHBOARD`, you can also access:


---

## 2. Models in the Admin

### 2.1 Testimonial Categories
- **Location in Admin:** `Testimonials → Testimonial Categories`
- **Purpose:** Organize testimonials into categories.
- **Fields:**
- `Name` — Category name.
- `Slug` — Auto-filled from the name (can be edited).
- `Description` — Optional text about the category.
- `Is Active` — Toggle category visibility.
- `Order` — Sorting order.
- **Extra Info:**
- `Testimonials` column shows the count of testimonials in that category.

---

### 2.2 Testimonials
- **Location in Admin:** `Testimonials → Testimonials`
- **Purpose:** Manage individual testimonials.
- **Key Columns in List View:**
- **Author Name**
- **Company**
- **Rating** (shown as stars)
- **Status** (colored badge: Pending, Approved, Rejected, Featured, Archived)
- **Category**
- **Created At**
- **Media** (check mark if testimonial has media)
- **Filters:** Status, Rating, Category, Created Date, Anonymous, Verified
- **Actions:**
- **Approve selected testimonials** — Marks as approved, sets `approved_at` and `approved_by`.
- **Reject selected testimonials** — Opens a form to add a rejection reason.
- **Feature selected testimonials** — Highlights testimonials as featured.
- **Archive selected testimonials** — Moves testimonials to archived state.

**Editing a Testimonial:**
- Organized into sections:
1. **Author Information** — Details of the author, company, location, avatar.
2. **Testimonial Content** — Title, content, rating, response.
3. **Categorization** — Category and source.
4. **Status and Moderation** — Status, anonymity, verification, display order, approval info, rejection reason.
5. **Additional Information** — Slug, website, social media links, IP address, extra data.
6. **Metadata** — Created/updated timestamps (read-only).

**Inline Media Management:**
- You can add `Testimonial Media` directly when editing a testimonial.
- Fields: file, media type, title, primary flag, order.

---

### 2.3 Testimonial Media
- **Location in Admin:** `Testimonials → Testimonial Media`
- **Purpose:** Manage media files attached to testimonials.
- **Key Columns in List View:**
- Thumbnail (image/video/audio/document icon)
- Linked testimonial
- Media type
- Primary flag
- Order
- Created date
- **Editing Media:**
- Add or edit files, type, title, description, set as primary, and order.
- Preview is available for images, video, and audio.
- Documents can be opened via a "View Document" link.

---

## 3. Status Color Codes
| Status       | Color   | Meaning                                          |
|--------------|---------|--------------------------------------------------|
| Pending      | Orange  | Awaiting moderation                              |
| Approved     | Green   | Published and visible                            |
| Rejected     | Red     | Not accepted; rejection reason stored            |
| Featured     | Blue    | Highlighted testimonial                          |
| Archived     | Grey    | Hidden from public but stored in the system      |

---

## 4. Custom Dashboard (Optional)
If `TESTIMONIALS_ENABLE_DASHBOARD = True` in `settings.py`, a separate testimonials-only admin site will be available at:

This dashboard only manages testimonial-related models.

---

## 5. Tips for Admins
- Use filters to quickly find testimonials awaiting moderation.
- When rejecting testimonials, always provide a clear rejection reason.
- Mark high-quality testimonials as **Featured** for special display.
- Regularly check media items for accuracy and appropriateness.
- Use `is_primary` on media to control which image/video is displayed first.

---

## 6. Contact for Support
If you encounter any issues, contact the technical team with:
- A description of the problem
- The testimonial ID or category affected
- The time the issue occurred
