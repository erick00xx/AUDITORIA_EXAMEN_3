import { useState, type FormEvent } from 'react';
import ChatLayout from './components/ChatLayout';

export interface Message {
  id: number;
  content: string;
  sender: 'user' | 'bot';
}

// Mensaje inicial mejorado
const initialMessage: Message = {
  id: 0,
  content: "Hola, soy EPIS Pilot, el asistente virtual de EPIS Corp. ¿En qué puedo ayudarte hoy?",
  sender: 'bot',
};

function App() {
  const [messages, setMessages] = useState<Message[]>([initialMessage]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showFeedbackButtons, setShowFeedbackButtons] = useState(false);
  const [showFollowUpOptions, setShowFollowUpOptions] = useState(false);
  
  // --- CAMBIO 1: Este estado ya no es necesario, lo eliminamos ---
  // const [lastProblemDescription, setLastProblemDescription] = useState<string>('');
  
  // --- CAMBIO 2: Nuevo estado para saber si estamos esperando la descripción de un ticket ---
  const [isWaitingForTicketDescription, setIsWaitingForTicketDescription] = useState(false);

  const sendMessage = async (messageToSend: string, isInternalAction = false) => {
    setShowFeedbackButtons(false);
    setShowFollowUpOptions(false);

    let finalMessage = messageToSend;

    // --- CAMBIO 3: Lógica para formatear la descripción del ticket ---
    // Si estamos esperando una descripción, la formateamos como una acción para el backend.
    if (isWaitingForTicketDescription && !isInternalAction) {
      finalMessage = `ACTION_CREATE_TICKET:${messageToSend}`;
      setIsWaitingForTicketDescription(false); // Reseteamos el estado
      isInternalAction = true; // Marcamos como acción interna para no mostrar "ACTION_..." en el chat
    }
    
    if (!isInternalAction) {
      const userMessage: Message = { id: Date.now(), sender: 'user', content: messageToSend };
      setMessages((prev) => [...prev, userMessage]);
      // Ya no necesitamos guardar la descripción original aquí
    }
    
    setIsLoading(true);
    setInput('');

    try {
      // La petición ahora usa 'finalMessage', que puede ser la pregunta normal o la acción del ticket
      const response = await fetch(`/api/ask?question=${encodeURIComponent(finalMessage)}`);
      if (!response.ok) throw new Error('Error en la respuesta de la red');

      const data = await response.json();
      const botMessage: Message = { id: Date.now() + 1, sender: 'bot', content: data.answer };
      setMessages((prev) => [...prev, botMessage]);

      if (data.follow_up_required) {
        setShowFeedbackButtons(true);
      }
    } catch (error) {
      console.error("Error al contactar la API:", error);
      const errorMessage: Message = { id: Date.now() + 1, sender: 'bot', content: "Error: No se pudo obtener respuesta del servidor." };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
  };

  const handleFeedback = (response: 'yes' | 'no') => {
    setShowFeedbackButtons(false);
    if (response === 'yes') {
      const confirmationMessage: Message = { id: Date.now(), sender: 'bot', content: "¡Genial! Me alegro de haberte ayudado. Si necesitas algo más, no dudes en preguntar." };
      setMessages((prev) => [...prev, confirmationMessage]);
    } else {
      const followUpMessage: Message = { id: Date.now(), sender: 'bot', content: "Entendido. ¿Cómo quieres proceder?" };
      setMessages((prev) => [...prev, followUpMessage]);
      setShowFollowUpOptions(true);
    }
  };

  const handleFollowUpChoice = (choice: 'create_ticket' | 'explain_more') => {
    setShowFollowUpOptions(false);
    
    // --- CAMBIO 4: Lógica de 'create_ticket' modificada ---
    if (choice === 'create_ticket') {
      // En lugar de crear el ticket, el bot ahora pregunta por los detalles.
      const askForDescriptionMessage: Message = { id: Date.now(), sender: 'bot', content: "De acuerdo. Por favor, explique su problema con detalle para que un experto le atienda. Lo que escriba a continuación se registrará en el ticket." };
      setMessages((prev) => [...prev, askForDescriptionMessage]);
      setIsWaitingForTicketDescription(true); // Activamos el modo "espera de descripción"
    } else {
      const explainMoreMessage: Message = { id: Date.now(), sender: 'bot', content: "Por favor, describe tu problema con más detalle en el chat." };
      setMessages((prev) => [...prev, explainMoreMessage]);
    }
  };

  return (
    <ChatLayout
      messages={messages}
      input={input}
      setInput={setInput}
      handleSubmit={handleSubmit}
      isLoading={isLoading}
      showFeedbackButtons={showFeedbackButtons}
      onFeedback={handleFeedback}
      showFollowUpOptions={showFollowUpOptions}
      onFollowUpChoice={handleFollowUpChoice}
    />
  );
}

export default App;