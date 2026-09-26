/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_REFERRAL_CHASE_SAPPHIRE?: string;
  readonly VITE_REFERRAL_CHASE_MARRIOTT?: string;
  readonly VITE_REFERRAL_CHASE_INK?: string;
  readonly VITE_REFERRAL_AMEX?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
