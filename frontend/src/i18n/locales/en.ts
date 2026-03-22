export const en = {
  // Login
  "login.title": "Avatar Server",

  "login.email": "Email",
  "login.password": "Password",
  "login.submit": "Sign in",
  "login.error": "Invalid credentials",
  "login.sso": "Sign in with SSO",
  "login.sso.error": "SSO login failed",
  "login.sso.loading": "Processing login...",
  "login.legacy": "Legacy Login",
  "login.legacy.divider": "or",
  "login.dev": "Dev Mode",

  // Upload
  "upload.title": "Upload Avatar",
  "upload.dropzone": "Drag image here or click",
  "upload.dropzone.hint": "JPG, PNG, WebP",
  "upload.btn.other": "Choose different image",
  "upload.btn.upload": "Upload",
  "upload.btn.uploading": "Uploading...",
  "upload.btn.new": "Upload new image",
  "upload.error": "Upload failed",
  "upload.limit": "Maximum number of avatars reached. Delete an existing avatar to upload a new one.",
  "upload.url.divider": "or",
  "upload.url.placeholder": "Enter image URL",
  "upload.url.load": "Load",
  "upload.url.error": "Could not load image",

  // Preview
  "preview.title": "Your Avatar",

  // History
  "history.title": "My Avatars",
  "history.active": "Active",
  "history.activate": "Use",
  "history.delete": "Remove",
  "history.delete.confirm": "Really remove this avatar?",
  "history.empty": "No avatars uploaded yet",
  "history.active.cannot_delete": "Active avatar cannot be removed",
  "crop.pan.hint": "Hold middle mouse button to pan",
  "crop.cancel": "Cancel",

  "history.edit": "Edit",
  "history.recrop.save": "Save",

  // User menu
  "usermenu.settings": "Account Settings",
  "usermenu.admin": "Admin Console",
  "usermenu.logout": "Logout",

  // Public URL
  "preview.url.label": "Public URL",
  "preview.url.copied": "Copied!",
  "preview.url.hint": "?s= at the end of the URL sets the size (e.g. ?s=256). Click a preview to change.",
  "preview.url.sizes": "Available sizes:",

  // Account Settings
  "settings.title": "Account Settings",
  "settings.back": "Back",
  "settings.profile.title": "Profile",
  "settings.profile.name": "Name",
  "settings.profile.email": "Email",
  "settings.language.title": "Language",
  "settings.language.de": "Deutsch",
  "settings.language.en": "English",
  "settings.danger.title": "Danger Zone",
  "settings.danger.description": "Permanently delete all avatars and data. This action cannot be undone.",
  "settings.danger.button": "Delete all data",
  "settings.danger.confirm": "Really delete all data? This action cannot be undone.",
  "settings.danger.confirm.button": "Delete permanently",

  // Admin Console
  "admin.title": "Admin Console",
  "admin.back": "Back",
  "admin.users.title": "User Management",
  "admin.users.email": "Email",
  "admin.users.name": "Name",
  "admin.users.source": "Source",
  "admin.users.admin": "Admin",
  "admin.users.avatars": "Avatars",
  "admin.users.created": "Created",
  "admin.users.actions": "Actions",
  "admin.users.delete.confirm": "Really delete this user and all their data?",
  "admin.users.create": "Create user",
  "admin.users.create.title": "Create new user",
  "admin.users.password": "Password",
  "admin.users.create.submit": "Create",
  "admin.users.create.error.exists": "Email already taken",
  "admin.users.edit.title": "Edit user",
  "admin.users.edit.save": "Save",
  "admin.users.edit.password.hint": "Leave empty to keep current password",
  "admin.users.active": "Active",
  "admin.users.deactivated": "Deactivated",
  "admin.users.deactivate.self": "Cannot deactivate your own account",
  "admin.settings.title": "Settings",
  "admin.settings.key": "Setting",
  "admin.settings.value": "Value",
  "admin.settings.source": "Source",
  "admin.settings.save": "Save",
  "admin.settings.reset": "Reset",
  "admin.settings.reset.tooltip": "Reset to ENV default",

  // Toast
  "toast.saved": "Saved",

  // Dialoge
  "dialog.cancel": "Cancel",
  "dialog.delete.confirm": "Remove",
} as const;
