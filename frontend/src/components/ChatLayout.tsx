import { type FormEvent, useRef, useEffect } from 'react';
import { Box, Paper, Typography, TextField, IconButton, CircularProgress, Button, Stack } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AddIcon from '@mui/icons-material/Add';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ReactMarkdown from 'react-markdown';
import { type Message } from '../App';

interface ChatLayoutProps {
  messages: Message[];
  input: string;
  setInput: (value: string) => void;
  handleSubmit: (e: FormEvent) => void;
  isLoading: boolean;
  showFeedbackButtons: boolean;
  onFeedback: (response: 'yes' | 'no') => void;
  showFollowUpOptions: boolean;
  onFollowUpChoice: (choice: 'create_ticket' | 'explain_more') => void;
}

export default function ChatLayout({ 
  messages, input, setInput, handleSubmit, isLoading, 
  showFeedbackButtons, onFeedback,
  showFollowUpOptions, onFollowUpChoice
}: ChatLayoutProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, showFeedbackButtons, showFollowUpOptions]); // Añadimos dependencias

  return (
    <Box sx={{ display: 'flex', height: '100vh', bgcolor: '#f5f5f5' }}>
      <Box sx={{ width: 280, bgcolor: '#ffffff', borderRight: '1px solid #e0e0e0', display: { xs: 'none', md: 'flex' }, flexDirection: 'column' }}>
        <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0' }}>
          <Button variant="outlined" fullWidth startIcon={<AddIcon />} onClick={() => window.location.reload()}>
            Nueva Conversación
          </Button>
        </Box>
        <Box sx={{ p: 2 }}>
          <Typography variant="body2" color="text.secondary">El historial de chats se ha omitido en esta versión.</Typography>
        </Box>
      </Box>
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', p: 2, maxHeight: '100vh' }}>
        <Paper elevation={2} sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Box sx={{ p: 2, borderBottom: '1px solid #e0e0e0', display: 'flex', alignItems: 'center', gap: 2 }}>
            <SmartToyIcon color="primary" />
            <Typography variant="h5" component="h1" sx={{ fontWeight: 700 }}>Corporate EPIS Pilot</Typography>
          </Box>
          <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
            {messages.map((msg) => (
               <Box key={msg.id} sx={{ mb: 2, display: 'flex', justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start' }}>
                <Paper elevation={1} sx={{ p: 1.5, maxWidth: '70%', bgcolor: msg.sender === 'user' ? 'primary.main' : 'grey.200', color: msg.sender === 'user' ? 'primary.contrastText' : 'text.primary', borderRadius: msg.sender === 'user' ? '20px 20px 5px 20px' : '20px 20px 20px 5px' }}>
                  <Typography variant="body1" component="div"><ReactMarkdown>{msg.content || '...'}</ReactMarkdown></Typography>
                </Paper>
              </Box>
            ))}
            {isLoading && <CircularProgress size={24} sx={{m:2}}/>}
            
            {/* Botones de Feedback Inicial (Sí/No) */}
            {showFeedbackButtons && (
              <Box sx={{ display: 'flex', justifyContent: 'flex-start', ml: 1, mt: 1 }}>
                <Stack direction="row" spacing={1}>
                  <Button variant="outlined" size="small" onClick={() => onFeedback('yes')}>Sí, solucionado</Button>
                  <Button variant="contained" size="small" onClick={() => onFeedback('no')}>No, necesito más ayuda</Button>
                </Stack>
              </Box>
            )}

            {/* Botones de Siguientes Pasos (Abrir Ticket / Explicar mejor) */}
            {showFollowUpOptions && (
              <Box sx={{ display: 'flex', justifyContent: 'flex-start', ml: 1, mt: 1 }}>
                <Stack direction="row" spacing={1}>
                  <Button variant="contained" size="small" onClick={() => onFollowUpChoice('create_ticket')}>Abrir un ticket</Button>
                  <Button variant="outlined" size="small" onClick={() => onFollowUpChoice('explain_more')}>Explicar mejor mi problema</Button>
                </Stack>
              </Box>
            )}

            <div ref={messagesEndRef} />
          </Box>
          <Box sx={{ p: 2, borderTop: '1px solid #e0e0e0' }}>
             <form onSubmit={handleSubmit} style={{ display: 'flex' }}>
               <TextField 
                 fullWidth 
                 variant="outlined" 
                 placeholder="Escribe tu pregunta..." 
                 value={input} 
                 onChange={(e) => setInput(e.target.value)} 
                 // El input se deshabilita si se está esperando una acción del usuario en CUALQUIER grupo de botones
                 disabled={isLoading || showFeedbackButtons || showFollowUpOptions} 
                 autoFocus 
                 onKeyPress={(e) => {if (e.key === 'Enter' && !e.shiftKey) { handleSubmit(e);}}}
               />
               <IconButton 
                 color="primary" 
                 type="submit" 
                 disabled={isLoading || showFeedbackButtons || showFollowUpOptions} 
                 sx={{ ml: 1 }}
               >
                 <SendIcon />
               </IconButton>
             </form>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
}