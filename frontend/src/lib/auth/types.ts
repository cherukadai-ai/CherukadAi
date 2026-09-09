/** Shared auth/session types mirrored from the backend's entitlement payload. */

export interface OrgUserSession {
  userId: string;
  organisationId: string;
  organisationSlug: string;
  email: string;
  displayName: string;
  isPlatformAdmin: false;
  permissions: string[];
  enabledFeatures: string[];
}

export interface PlatformAdminSession {
  userId: string;
  isPlatformAdmin: true;
  email: string;
  displayName: string;
}

export type Session = OrgUserSession | PlatformAdminSession | null;
