import { motion } from 'framer-motion';

const Hero = () => {
  return (
    <section style={{ 
      height: '100vh', 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      textAlign: 'center',
      padding: '0 2rem'
    }}>
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        style={{ 
          fontFamily: 'Technical', 
          fontSize: '1rem', 
          color: 'var(--accent)',
          marginBottom: '1.5rem',
          letterSpacing: '0.2em'
        }}
      >
        [ i18n-agent-skill ]
      </motion.div>

      <motion.h1 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
        style={{ 
          fontFamily: 'Technical', 
          fontSize: 'clamp(2.5rem, 6vw, 4.5rem)', 
          color: '#ffffff',
          textShadow: '0 0 20px rgba(88, 166, 255, 0.4), 0 0 40px rgba(88, 166, 255, 0.1)',
          marginBottom: '1.5rem',
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          lineHeight: '1.1'
        }}
      >
        Industrial-Grade<br/>
        <span style={{ color: 'var(--primary)' }}>I18n Lifecycle</span> Engine
      </motion.h1>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5, duration: 1 }}
        style={{ 
          maxWidth: '650px', 
          color: 'var(--text-muted)',
          fontSize: '1.15rem',
          lineHeight: '1.8',
          marginBottom: '3.5rem',
          fontWeight: 300
        }}
      >
        Built for scale. High-precision AST extraction, built-in Privacy Shield,<br/>driving internationalization from 'Search' to 'Evolution'.
      </motion.p>

      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7, duration: 0.6 }}
        style={{ display: 'flex', gap: '1.5rem', justifyContent: 'center' }}
      >
        <a href="https://github.com/Shirolin/i18n-agent-skill" target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>
          <button style={{
            padding: '0.8rem 2.5rem',
            background: 'linear-gradient(135deg, var(--primary), #3b82f6)',
            color: '#fff',
            border: 'none',
            fontWeight: '600',
            cursor: 'pointer',
            borderRadius: '4px',
            fontFamily: 'Technical',
            letterSpacing: '0.1em',
            boxShadow: '0 4px 15px rgba(88, 166, 255, 0.3)',
            transition: 'all 0.3s ease',
            fontSize: '0.95rem'
          }}
          onMouseOver={e => e.currentTarget.style.boxShadow = '0 6px 25px rgba(88, 166, 255, 0.5)'}
          onMouseOut={e => e.currentTarget.style.boxShadow = '0 4px 15px rgba(88, 166, 255, 0.3)'}
          >
            GET STARTED
          </button>
        </a>
        <a href="https://github.com/Shirolin/i18n-agent-skill/blob/main/SKILL.md" target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none' }}>
          <button style={{
            padding: '0.8rem 2.5rem',
            backgroundColor: 'rgba(88, 166, 255, 0.05)',
            color: 'var(--primary)',
            border: '1px solid rgba(88, 166, 255, 0.4)',
            fontWeight: '600',
            cursor: 'pointer',
            borderRadius: '4px',
            fontFamily: 'Technical',
            letterSpacing: '0.1em',
            backdropFilter: 'blur(4px)',
            transition: 'all 0.3s ease',
            fontSize: '0.95rem'
          }}
          onMouseOver={e => {
            e.currentTarget.style.backgroundColor = 'rgba(88, 166, 255, 0.1)';
            e.currentTarget.style.borderColor = 'var(--primary)';
          }}
          onMouseOut={e => {
            e.currentTarget.style.backgroundColor = 'rgba(88, 166, 255, 0.05)';
            e.currentTarget.style.borderColor = 'rgba(88, 166, 255, 0.4)';
          }}
          >
            DOCUMENTATION
          </button>
        </a>
      </motion.div>
    </section>
  );
};

export default Hero;
