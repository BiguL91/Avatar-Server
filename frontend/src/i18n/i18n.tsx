import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { de } from "./locales/de";
import { en } from "./locales/en";

export type TranslationKey = keyof typeof de;

const locales: Record<string, Record<string, string>> = { de, en };

interface I18nContextType {
  lang: string;
  t: (key: TranslationKey) => string;
  setLang: (lang: string) => void;
  availableLanguages: string[];
}

const I18nContext = createContext<I18nContextType | null>(null);

interface I18nProviderProps {
  defaultLang?: string;
  children: ReactNode;
}

export function I18nProvider({ defaultLang = "de", children }: I18nProviderProps) {
  const [lang, setLang] = useState(defaultLang);

  // Sprache aktualisieren wenn defaultLang sich aendert (z.B. nach Config-Laden)
  useEffect(() => {
    setLang(defaultLang);
  }, [defaultLang]);

  const t = useCallback(
    (key: TranslationKey): string => {
      // Aktuelle Sprache -> Fallback Deutsch -> Key selbst
      return locales[lang]?.[key] ?? locales["de"]?.[key] ?? key;
    },
    [lang]
  );

  const availableLanguages = Object.keys(locales);

  return (
    <I18nContext.Provider value={{ lang, t, setLang, availableLanguages }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslation() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useTranslation muss innerhalb von I18nProvider verwendet werden");
  }
  return context;
}
