"use client";

import Image from "next/image";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

import { cn } from "@/lib/utils";
import { vapi } from "@/lib/vapi.sdk";
import { interviewer } from "@/constants";
import { createFeedback } from "@/lib/actions/general.action";

enum CallStatus {
 INACTIVE = "INACTIVE",
 CONNECTING = "CONNECTING",
 ACTIVE = "ACTIVE",
 FINISHED = "FINISHED",
}

interface SavedMessage {
 role: "user" \| "system" \| "assistant";
 content: string;
}

const Agent = ({
 userName,
 userId,
 interviewId,
 feedbackId,
 type,
 questions,
}: AgentProps) => {
 const router = useRouter();
 const \[callStatus, setCallStatus\] = useState(CallStatus.INACTIVE);
 const \[messages, setMessages\] = useState(\[\]);
 const \[isSpeaking, setIsSpeaking\] = useState(false);
 const \[lastMessage, setLastMessage\] = useState("");

 useEffect(() => {
 const onCallStart = () => {
 setCallStatus(CallStatus.ACTIVE);
 };

 const onCallEnd = () => {
 setCallStatus(CallStatus.FINISHED);
 };

 const onMessage = (message: Message) => {
 if (message.type === "transcript" && message.transcriptType === "final") {
 const newMessage = { role: message.role, content: message.transcript };
 setMessages((prev) => \[...prev, newMessage\]);
 }
 };

 const onSpeechStart = () => {
 console.log("speech start");
 setIsSpeaking(true);
 };

 const onSpeechEnd = () => {
 console.log("speech end");
 setIsSpeaking(false);
 };

 const onError = (error: Error) => {
 console.log("Error:", error);
 };

 vapi.on("call-start", onCallStart);
 vapi.on("call-end", onCallEnd);
 vapi.on("message", onMessage);
 vapi.on("speech-start", onSpeechStart);
 vapi.on("speech-end", onSpeechEnd);
 vapi.on("error", onError);

 return () => {
 vapi.off("call-start", onCallStart);
 vapi.off("call-end", onCallEnd);
 vapi.off("message", onMessage);
 vapi.off("speech-start", onSpeechStart);
 vapi.off("speech-end", onSpeechEnd);
 vapi.off("error", onError);
 };
 }, \[\]);

 useEffect(() => {
 if (messages.length > 0) {
 setLastMessage(messages\[messages.length - 1\].content);
 }

 const handleGenerateFeedback = async (messages: SavedMessage\[\]) => {
 console.log("handleGenerateFeedback");

 const { success, feedbackId: id } = await createFeedback({
 interviewId: interviewId!,
 userId: userId!,
 transcript: messages,
 feedbackId,
 });

 if (success && id) {
 router.push(\`/interview/${interviewId}/feedback\`);
 } else {
 console.log("Error saving feedback");
 router.push("/");
 }
 };

 if (callStatus === CallStatus.FINISHED) {
 if (type === "generate") {
 router.push("/");
 } else {
 handleGenerateFeedback(messages);
 }
 }
 }, \[messages, callStatus, feedbackId, interviewId, router, type, userId\]);

 const handleCall = async () => {
 setCallStatus(CallStatus.CONNECTING);

 if (type === "generate") {
 await vapi.start(process.env.NEXT\_PUBLIC\_VAPI\_WORKFLOW\_ID!, {
 variableValues: {
 username: userName,
 userid: userId,
 },
 });
 } else {
 let formattedQuestions = "";
 if (questions) {
 formattedQuestions = questions
 .map((question) => \`- ${question}\`)
 .join("\\n");
 }

 await vapi.start(interviewer, {
 variableValues: {
 questions: formattedQuestions,
 },
 });
 }
 };

 const handleDisconnect = () => {
 setCallStatus(CallStatus.FINISHED);
 vapi.stop();
 };

 return (
 <>


{/\\* AI Interviewer Card \*/}


![profile-image](https://raw.githubusercontent.com/ai-avatar.png)
{isSpeaking && }


### AI Interviewer

{/\\* User Profile Card \*/}


![profile-image](https://raw.githubusercontent.com/user-avatar.png)

### {userName}

 {messages.length > 0 && (


{lastMessage}


 )}



{callStatus !== "ACTIVE" ? (
handleCall()}>

{callStatus === "INACTIVE" \|\| callStatus === "FINISHED"
? "Call"
: ". . ."}

) : (
handleDisconnect()}>
End

)}



 );
};

export default Agent;