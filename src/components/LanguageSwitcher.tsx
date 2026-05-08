import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Globe } from 'lucide-react';

const LanguageSwitcher = () => {
  const { i18n } = useTranslation();

  const toggleLanguage = () => {
    const newLang = i18n.language === 'en' ? 'zh' : 'en';
    i18n.changeLanguage(newLang);
  };

  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={toggleLanguage}
      className="hud-panel"
      style={{
        position: 'fixed',
        top: '2rem',
        right: '2rem',
        zIndex: 1000,
        background: 'rgba(13, 17, 23, 0.8)',
        border: '1px solid rgba(88, 166, 255, 0.4)',
        color: 'var(--primary)',
        padding: '0.6rem 1rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem',
        cursor: 'pointer',
        fontFamily: 'Technical',
        fontWeight: 'bold',
        fontSize: '0.9rem',
        letterSpacing: '0.05em'
      }}
    >
      <Globe size={18} />
      {i18n.language === 'en' ? '中文' : 'EN'}
    </motion.button>
  );
};

export default LanguageSwitcher;
