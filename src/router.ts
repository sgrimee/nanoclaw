import path from 'path';
import { STORE_DIR } from './config.js';
import { Channel, NewMessage } from './types.js';

export function escapeXml(s: string): string {
  if (!s) return '';
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function formatMessages(messages: NewMessage[]): string {
  const lines = messages.map((m) => {
    let messageContent = `<message sender="${escapeXml(m.sender_name)}" time="${m.timestamp}">`;

    if (m.media_path && m.media_mime_type) {
      // Convert host media path to container path
      // Host: /path/to/project/store/media/file.jpg -> Container: /workspace/media/file.jpg
      let containerMediaPath = m.media_path;
      const mediaDir = path.join(STORE_DIR, 'media');
      if (m.media_path.startsWith(mediaDir)) {
        // Extract just the filename
        const filename = path.basename(m.media_path);
        containerMediaPath = `/workspace/media/${filename}`;
      }
      // Include media as attachment that Claude can read
      const mime = m.media_mime_type ?? '';
      const tag = mime.startsWith('image/')
        ? 'Image'
        : mime === 'application/pdf'
          ? 'PDF'
          : mime.includes('word') || mime.includes('document')
            ? 'Document'
            : 'File';
      // For non-image files add an explicit read hint — images work without it
      // because Claude natively handles image reads, but PDFs/docs need prompting.
      const readHint = mime.startsWith('image/')
        ? ''
        : ' — use Read tool to view contents';
      // Attachment reference goes FIRST so the agent sees the file before any
      // caption/question. If the caption is just the placeholder tag, omit it.
      const placeholderTag = `[${tag}]`;
      const caption =
        m.content && m.content !== placeholderTag
          ? `\n${escapeXml(m.content)}`
          : '';
      messageContent += `[${tag}: ${containerMediaPath}${readHint}]${caption}`;
    } else {
      messageContent += escapeXml(m.content);
    }

    messageContent += `</message>`;
    return messageContent;
  });
  return `<messages>\n${lines.join('\n')}\n</messages>`;
}

export function stripInternalTags(text: string): string {
  return text.replace(/<internal>[\s\S]*?<\/internal>/g, '').trim();
}

export function formatOutbound(rawText: string): string {
  const text = stripInternalTags(rawText);
  if (!text) return '';
  return text;
}

export function routeOutbound(
  channels: Channel[],
  jid: string,
  text: string,
): Promise<void> {
  const channel = channels.find((c) => c.ownsJid(jid) && c.isConnected());
  if (!channel) throw new Error(`No channel for JID: ${jid}`);
  return channel.sendMessage(jid, text);
}

export function findChannel(
  channels: Channel[],
  jid: string,
): Channel | undefined {
  return channels.find((c) => c.ownsJid(jid));
}
