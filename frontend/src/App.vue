<template>
  <div class="app-container" :class="{ 'dark-mode': isDarkMode, 'sidebar-open': showSidebar }">
    <!-- 导航栏 -->
    <nav class="navbar">
      <div class="navbar-content">
        <div class="nav-left">
          <button class="sidebar-toggle" @click="toggleSidebar" title="切换侧边栏">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
          <div class="nav-links">
            <button 
              class="nav-item" 
              :class="{ active: currentPage === 'chat' }"
              @click="switchPage('chat')"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
              </svg>
              <span>聊天界面</span>
            </button>
          </div>
        </div>
        <button class="theme-toggle" @click="toggleTheme">
          <svg v-if="isDarkMode" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        </button>
      </div>
    </nav>
    
    <!-- 侧边栏 - 历史记录 -->
    <aside class="sidebar" :class="{ 'sidebar-open': showSidebar }">
      <div class="sidebar-header">
        <h3>对话历史</h3>
        <button class="new-chat-btn" @click="createNewChat" title="新建对话">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
        </button>
      </div>
      <div class="chat-list">
        <div 
          v-for="chat in chatHistory" 
          :key="chat.threadId"
          class="chat-item"
          :class="{ active: currentThreadId === chat.threadId }"
          @click="switchChat(chat.threadId)"
        >
          <div class="chat-item-content">
            <div class="chat-item-title">{{ chat.title || '新对话' }}</div>
            <div class="chat-item-time">{{ formatChatTime(chat.lastUpdate) }}</div>
          </div>
          <button class="chat-item-delete" @click.stop="deleteChat(chat.threadId)" title="删除对话">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
        <div v-if="chatHistory.length === 0" class="empty-chat-list">
          <p>暂无对话记录</p>
          <p class="empty-hint">开始一个新对话吧！</p>
        </div>
      </div>
    </aside>
    
    <!-- 侧边栏遮罩 -->
    <div v-if="showSidebar" class="sidebar-overlay" @click="toggleSidebar"></div>
    
    <main class="main-content">
      <div v-if="currentPage === 'chat'" class="chat-container" :class="{ resizing: isResizing }" :style="{ width: chatWidth + 'px' }" ref="chatContainer">
        <!-- 可调整大小的拖拽条 -->
        <div 
          class="resizer" 
          @mousedown="startResize"
          @touchstart="startResize"
        ></div>
        <!-- 顶部栏 -->
        <div class="chat-header">
          <div class="header-content">
            <div class="status-dot"></div>
            <h2>多Agent研究助手</h2>
          </div>
          <div class="header-subtitle">Powered by LangGraph</div>
        </div>
        
        <!-- 消息列表 -->
        <div class="messages" ref="messagesContainer">
          <div v-if="messages.length === 0" class="welcome-message">
            <div class="welcome-icon">👋</div>
            <p>欢迎使用多Agent研究助手！</p>
            <p>请输入你的问题，我会为你进行规划、研究和写作。</p>
          </div>

          <div
            v-for="(msg, index) in messages"
            :key="`${msg.conversationId || 0}-${msg.type}-${index}`"
            :class="['message-row', msg.type]"
          >
            <div class="avatar">
              <span v-if="msg.type === 'user'">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>
                  <circle cx="12" cy="7" r="4"/>
                </svg>
              </span>
              <span v-else-if="msg.type === 'plan'">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                  <polyline points="10 9 9 9 8 9"/>
                </svg>
              </span>
              <span v-else-if="msg.type === 'research'">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="11" cy="11" r="8"/>
                  <path d="m21 21-4.35-4.35"/>
                </svg>
              </span>
              <span v-else-if="msg.type === 'answer'">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                  <path d="M14 2v6h6"/>
                  <path d="M16 13H8"/>
                  <path d="M16 17H8"/>
                  <path d="M10 9H8"/>
                </svg>
              </span>
              <span v-else-if="msg.type === 'system'">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <path d="M12 16v-4"/>
                  <path d="M12 8h.01"/>
                </svg>
              </span>
              <span v-else>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                  <line x1="12" y1="8" x2="12" y2="12"/>
                  <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
              </span>
            </div>
            <div class="message-bubble">
              <div 
                v-if="shouldRenderMarkdown(msg.type)" 
                class="message-content markdown-body" 
                v-html="renderMarkdown(msg.content)"
              ></div>
              <div v-else class="message-content">{{ msg.content }}</div>
            </div>
          </div>

          <div v-if="isLoading" class="loading-indicator">
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
            <span>处理中...</span>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <div class="input-box">
            <textarea
              v-model="inputText"
              @keydown.enter.exact.prevent="handleSend"
              @keydown.shift.enter.exact="inputText += '\n'"
              placeholder="输入你的问题... "
              :disabled="isLoading"
              rows="1"
              class="input-field"
              ref="inputField"
            ></textarea>
            <button
              @click="handleSend"
              :disabled="isLoading || !inputText.trim()"
              class="send-button"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"></line>
                <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { ref, nextTick, onMounted, onUnmounted, watch } from 'vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false, // 禁用 HTML 以防止 XSS
  linkify: true,
  breaks: true
})

export default {
  name: 'App',
  setup() {
    const inputText = ref('')
    const messages = ref([])
    const isLoading = ref(false)
    const messagesContainer = ref(null)
    const inputField = ref(null)
    const chatContainer = ref(null)
    
    // 当前页面
    const currentPage = ref('chat')
    
    // 主题模式
    const isDarkMode = ref(false)
    
    // 侧边栏状态
    const showSidebar = ref(false)
    
    // 对话管理
    const currentThreadId = ref(null)
    const chatHistory = ref([])
    
    // 当前对话轮次的唯一ID
    const currentConversationId = ref(0)
    
    // 从 localStorage 读取主题设置
    onMounted(() => {
      const savedTheme = localStorage.getItem('theme')
      if (savedTheme === 'dark') {
        isDarkMode.value = true
      }
    })
    
    // 监听主题变化，应用到 body
    watch(isDarkMode, (newVal) => {
      if (newVal) {
        document.body.classList.add('dark-mode')
        localStorage.setItem('theme', 'dark')
      } else {
        document.body.classList.remove('dark-mode')
        localStorage.setItem('theme', 'light')
      }
    }, { immediate: true })
    
    // 切换主题
    const toggleTheme = () => {
      isDarkMode.value = !isDarkMode.value
    }
    
    // 切换页面
    const switchPage = (page) => {
      if (page === 'chat') {
        currentPage.value = 'chat'
      }
      // 其他页面暂时不实现
    }
    
    // 切换侧边栏
    const toggleSidebar = () => {
      showSidebar.value = !showSidebar.value
    }
    
    // 创建新对话
    const createNewChat = async () => {
      currentThreadId.value = null
      messages.value = []
      inputText.value = ''
      // 重置对话轮次ID
      currentConversationId.value = 0
      await loadChatHistory()
      showSidebar.value = false
    }
    
    // 切换对话
    const switchChat = async (threadId) => {
      if (currentThreadId.value === threadId) {
        showSidebar.value = false
        return
      }
      
      currentThreadId.value = threadId
      messages.value = []
      // 重置对话轮次ID
      currentConversationId.value = 0
      isLoading.value = true
      
      try {
        // 加载历史消息
        await loadChatMessages(threadId)
        // 设置对话轮次ID为历史消息的最大值+1
        if (messages.value.length > 0) {
          const maxConvId = Math.max(...messages.value.map(m => m.conversationId || 0))
          currentConversationId.value = maxConvId + 1
        }
      } catch (error) {
        console.error('加载对话失败:', error)
        messages.value.push({
          type: 'error',
          content: `加载对话失败: ${error.message}`,
          timestamp: new Date(),
          conversationId: currentConversationId.value
        })
      } finally {
        isLoading.value = false
        showSidebar.value = false
        await scrollToBottom()
      }
    }
    
    // 删除对话
    const deleteChat = async (threadId) => {
      if (!confirm('确定要删除这个对话吗？')) {
        return
      }
      
      try {
        const apiUrl = import.meta.env.DEV ? '/api/chat/threads' : 'http://localhost:8000/api/chat/threads'
        const response = await fetch(`${apiUrl}/${threadId}`, {
          method: 'DELETE'
        })
        
        if (!response.ok) {
          throw new Error('删除失败')
        }
        
        // 如果删除的是当前对话，清空消息
        if (currentThreadId.value === threadId) {
          currentThreadId.value = null
          messages.value = []
        }
        
        // 重新加载历史记录
        await loadChatHistory()
      } catch (error) {
        console.error('删除对话失败:', error)
        alert('删除对话失败: ' + error.message)
      }
    }
    
    // 加载对话历史列表
    const loadChatHistory = async () => {
      try {
        const apiUrl = import.meta.env.DEV ? '/api/chat/threads' : 'http://localhost:8000/api/chat/threads'
        const response = await fetch(apiUrl)
        
        if (!response.ok) {
          throw new Error('加载历史记录失败')
        }
        
        const data = await response.json()
        chatHistory.value = data.threads || []
        
        // 按最后更新时间排序
        chatHistory.value.sort((a, b) => {
          return new Date(b.lastUpdate) - new Date(a.lastUpdate)
        })
      } catch (error) {
        console.error('加载历史记录失败:', error)
        chatHistory.value = []
      }
    }
    
    // 加载指定对话的消息
    const loadChatMessages = async (threadId) => {
      try {
        const apiUrl = import.meta.env.DEV ? '/api/chat/threads' : 'http://localhost:8000/api/chat/threads'
        const response = await fetch(`${apiUrl}/${threadId}/messages`)
        
        if (!response.ok) {
          throw new Error('加载消息失败')
        }
        
        const data = await response.json()
        // 为历史消息分配对话轮次ID（按顺序）
        let convId = 0
        const processedMessages = []
        for (const msg of (data.messages || [])) {
          // 如果是用户消息，开始新的对话轮次
          if (msg.type === 'user') {
            convId++
          }
          // 确保消息类型正确：将 assistant 映射为 answer（向后兼容）
          let msgType = msg.type || 'system'
          if (msgType === 'assistant') {
            msgType = 'answer'
          }
          processedMessages.push({
            type: msgType,
            content: msg.content || '',
            timestamp: new Date(msg.timestamp || Date.now()),
            conversationId: convId,
            finalized: true // 历史消息都是已完成的
          })
        }
        messages.value = processedMessages
      } catch (error) {
        console.error('加载消息失败:', error)
        throw error
      }
    }
    
    // 格式化对话时间
    const formatChatTime = (timestamp) => {
      if (!timestamp) return ''
      const date = new Date(timestamp)
      const now = new Date()
      const diff = now - date
      const days = Math.floor(diff / (1000 * 60 * 60 * 24))
      
      if (days === 0) {
        return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      } else if (days === 1) {
        return '昨天'
      } else if (days < 7) {
        return `${days}天前`
      } else {
        return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
      }
    }
    
    // 聊天窗口宽度，默认 950px，最小 400px，最大 1600px
    const defaultWidth = 950
    const minWidth = 400
    const maxWidth = 1600
    const chatWidth = ref(defaultWidth)
    
    // 从 localStorage 读取保存的宽度
    onMounted(() => {
      const savedWidth = localStorage.getItem('chatWidth')
      if (savedWidth) {
        const width = parseInt(savedWidth, 10)
        if (width >= minWidth && width <= maxWidth) {
          chatWidth.value = width
        }
      }
    })
    
    // 拖拽调整大小
    const isResizing = ref(false)
    let startX = 0
    let startWidth = 0
    
    const startResize = (e) => {
      isResizing.value = true
      startX = e.clientX || (e.touches && e.touches[0].clientX) || 0
      startWidth = chatWidth.value
      
      document.addEventListener('mousemove', handleResize)
      document.addEventListener('mouseup', stopResize)
      document.addEventListener('touchmove', handleResize)
      document.addEventListener('touchend', stopResize)
      
      // 防止文本选择
      document.body.style.userSelect = 'none'
      document.body.style.cursor = 'col-resize'
      
      e.preventDefault()
    }
    
    const handleResize = (e) => {
      if (!isResizing.value) return
      
      const clientX = e.clientX || (e.touches && e.touches[0].clientX) || 0
      const diff = clientX - startX
      // 由于拖拽条在左侧，反向计算宽度，让“向右拖变宽 / 向左拖变窄”的体验一致
      const newWidth = startWidth - diff
      
      // 限制宽度范围
      if (newWidth >= minWidth && newWidth <= maxWidth) {
        chatWidth.value = newWidth
      } else if (newWidth < minWidth) {
        chatWidth.value = minWidth
      } else if (newWidth > maxWidth) {
        chatWidth.value = maxWidth
      }
      
      // 保存到 localStorage
      localStorage.setItem('chatWidth', chatWidth.value.toString())
    }
    
    const stopResize = () => {
      isResizing.value = false
      document.removeEventListener('mousemove', handleResize)
      document.removeEventListener('mouseup', stopResize)
      document.removeEventListener('touchmove', handleResize)
      document.removeEventListener('touchend', stopResize)
      
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }
    
    // 清理事件监听器
    onUnmounted(() => {
      stopResize()
    })

    const scrollToBottom = async () => {
      await nextTick()
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    }

    const renderMarkdown = (text) => {
      return md.render(text || '')
    }

    const shouldRenderMarkdown = (type) => {
      // 对于 plan, research, answer 类型渲染 markdown
      return ['plan', 'research', 'answer'].includes(type)
    }

    const getMessageTypeLabel = (type) => {
      const labels = {
        user: '你',
        plan: '规划',
        research: '研究',
        answer: '答案',
        system: '系统',
        error: '错误'
      }
      return labels[type] || type
    }

    const formatTime = (timestamp) => {
      return new Date(timestamp).toLocaleTimeString('zh-CN')
    }

    const handleSend = async () => {
      const question = inputText.value.trim()
      if (!question || isLoading.value) return

      // 增加对话轮次ID
      currentConversationId.value += 1
      const conversationId = currentConversationId.value

      // 添加用户消息
      messages.value.push({
        type: 'user',
        content: question,
        timestamp: new Date(),
        conversationId: conversationId
      })

      inputText.value = ''
      isLoading.value = true
      await scrollToBottom()

      try {
        await streamChat(question, conversationId)
        // 发送成功后刷新历史记录
        await loadChatHistory()
      } catch (error) {
        console.error('Error:', error)
        messages.value.push({
          type: 'error',
          content: `错误: ${error.message}`,
          timestamp: new Date(),
          conversationId: conversationId
        })
      } finally {
        isLoading.value = false
        await scrollToBottom()
      }
    }

    const streamChat = async (question, conversationId) => {
      // 使用相对路径，通过 Vite 代理转发到后端
      const apiUrl = import.meta.env.DEV ? '/api/chat' : 'http://localhost:8000/api/chat'
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          question,
          thread_id: currentThreadId.value || undefined
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              handleStreamData(data, conversationId)
            } catch (e) {
              console.error('Parse error:', e)
            }
          }
        }
      }
    }

    const handleStreamData = (data, conversationId) => {
      switch (data.type) {
        case 'start':
          messages.value.push({
            type: 'system',
            content: data.message,
            timestamp: new Date(),
            conversationId: conversationId
          })
          // 如果是新对话，保存 thread_id
          if (data.thread_id && !currentThreadId.value) {
            currentThreadId.value = data.thread_id
          }
          break

        case 'plan':
          // 更新或创建计划消息（只匹配当前对话轮次）
          let planMsg = messages.value.find(m => m.type === 'plan' && m.conversationId === conversationId && !m.finalized)
          if (!planMsg) {
            planMsg = {
              type: 'plan',
              content: data.content,
              timestamp: new Date(),
              finalized: false,
              conversationId: conversationId
            }
            messages.value.push(planMsg)
          } else {
            planMsg.content = data.content
          }
          if (data.final) {
            planMsg.finalized = true
          }
          break

        case 'research':
          // 更新或创建研究消息（只匹配当前对话轮次）
          let researchMsg = messages.value.find(m => m.type === 'research' && m.conversationId === conversationId && !m.finalized)
          if (!researchMsg) {
            researchMsg = {
              type: 'research',
              content: data.content,
              timestamp: new Date(),
              finalized: false,
              conversationId: conversationId
            }
            messages.value.push(researchMsg)
          } else {
            researchMsg.content = data.content
          }
          if (data.final) {
            researchMsg.finalized = true
          }
          break

        case 'answer':
        case 'final':
          // 更新或创建答案消息（只匹配当前对话轮次）
          let answerMsg = messages.value.find(m => m.type === 'answer' && m.conversationId === conversationId && !m.finalized)
          if (!answerMsg) {
            answerMsg = {
              type: 'answer',
              content: data.content,
              timestamp: new Date(),
              finalized: false,
              conversationId: conversationId
            }
            messages.value.push(answerMsg)
          } else {
            answerMsg.content = data.content
          }
          if (data.final) {
            answerMsg.finalized = true
          }
          break

        case 'error':
          messages.value.push({
            type: 'error',
            content: data.message,
            timestamp: new Date(),
            conversationId: conversationId
          })
          break

        case 'done':
          // 处理完成，更新 thread_id（如果有）
          if (data.thread_id) {
            currentThreadId.value = data.thread_id
          }
          break
      }

      // 滚动到底部
      nextTick(() => {
        scrollToBottom()
      })
    }
    
    // 监听当前对话 ID，持久化到 localStorage，便于刷新后恢复
    watch(currentThreadId, (newId) => {
      if (newId) {
        localStorage.setItem('currentThreadId', String(newId))
      } else {
        localStorage.removeItem('currentThreadId')
      }
    })

    // 初始化时加载历史记录，并尽量恢复上一次查看的对话
    onMounted(async () => {
      // 先加载对话历史列表
      await loadChatHistory()

      // 尝试从 localStorage 恢复上一次的对话
      const savedThreadId = localStorage.getItem('currentThreadId')
      if (savedThreadId) {
        const exists = chatHistory.value.some(
          (chat) => String(chat.threadId) === savedThreadId
        )
        if (exists) {
          await switchChat(savedThreadId)
          return
        } else {
          // 如果保存的对话已不存在，清理无效记录
          localStorage.removeItem('currentThreadId')
        }
      }

      // 如果没有保存的对话，但历史中有记录，则默认打开最近的一条
      if (chatHistory.value.length > 0) {
        await switchChat(chatHistory.value[0].threadId)
      }
    })

    return {
      inputText,
      messages,
      isLoading,
      messagesContainer,
      inputField,
      chatContainer,
      chatWidth,
      isResizing,
      startResize,
      handleSend,
      renderMarkdown,
      shouldRenderMarkdown,
      getMessageTypeLabel,
      formatTime,
      currentPage,
      isDarkMode,
      toggleTheme,
      switchPage,
      showSidebar,
      toggleSidebar,
      chatHistory,
      currentThreadId,
      createNewChat,
      switchChat,
      deleteChat,
      formatChatTime
    }
  }
}
</script>
