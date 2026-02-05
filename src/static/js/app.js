const { createApp } = Vue;

createApp({
    data() {
        return {
            subscriptions: [],
            reports: [],
            schedule: {
                time: '08:00',
                enabled: true
            },
            crawlSchedule: {
                enabled: true,
                times: ['06:00', '12:00', '18:00', '22:00']
            },
            showSubscriptionModal: false,
            showSettingsModal: false,
            newKeyword: '',
            generating: false,
            generatingOnly: false,
            collecting: false,
            viewingReport: null,
            notification: null,
            // Log panel
            logs: [],
            showLogPanel: false,
            logPanelWidth: 400,
            isResizing: false,
            autoScroll: true,
            logPollingInterval: null,
            lastLogTimestamp: null,
            // Background tasks
            activeTasks: [],  // List of active task IDs being polled
            taskPollingIntervals: {},  // task_id -> interval
            currentTask: null,  // Currently displayed task progress
            showTaskDialog: false
        };
    },
    
    mounted() {
        this.addLog('info', '🚀 应用已启动');
        this.loadSubscriptions();
        this.loadReports();
        this.loadSchedule();
        this.loadCrawlSchedule();
        
        // Start log polling (every 5 seconds)
        this.startLogPolling();
        
        // Add global mouse event listeners for resizing
        document.addEventListener('mousemove', this.handleResize);
        document.addEventListener('mouseup', this.stopResize);
    },
    
    beforeUnmount() {
        // Clean up polling interval
        if (this.logPollingInterval) {
            clearInterval(this.logPollingInterval);
        }
        // Clean up resize listeners
        document.removeEventListener('mousemove', this.handleResize);
        document.removeEventListener('mouseup', this.stopResize);
    },
    
    methods: {
        // Log Panel functions
        toggleLogPanel() {
            this.showLogPanel = !this.showLogPanel;
        },
        
        startResize(e) {
            this.isResizing = true;
            e.preventDefault();
        },
        
        handleResize(e) {
            if (!this.isResizing) return;
            const newWidth = window.innerWidth - e.clientX;
            if (newWidth >= 280 && newWidth <= 600) {
                this.logPanelWidth = newWidth;
            }
        },
        
        stopResize() {
            this.isResizing = false;
        },
        
        // Log functions
        addLog(level, message) {
            const time = new Date().toLocaleTimeString('zh-CN', { 
                hour12: false, 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
            const levelTexts = {
                info: 'INFO',
                success: 'OK',
                warning: 'WARN',
                error: 'ERROR'
            };
            
            this.logs.push({
                time,
                level,
                levelText: levelTexts[level] || 'INFO',
                message
            });
            
            // Auto scroll to bottom
            if (this.autoScroll) {
                this.$nextTick(() => {
                    const logList = this.$refs.logList;
                    if (logList) {
                        logList.scrollTop = logList.scrollHeight;
                    }
                });
            }
        },
        
        clearLogs() {
            this.logs = [];
            this.addLog('info', '日志已清空');
        },
        
        async fetchBackendLogs() {
            try {
                const response = await axios.get('/api/logs?count=50');
                const backendLogs = response.data.logs;
                
                // Merge backend logs with frontend logs (avoid duplicates)
                for (const log of backendLogs) {
                    const exists = this.logs.some(l => 
                        l.time === log.timestamp.substring(11, 19) && l.message === log.message
                    );
                    
                    if (!exists && log.timestamp) {
                        this.logs.push({
                            time: log.timestamp.substring(11, 19), // Extract HH:MM:SS
                            level: log.level,
                            levelText: {
                                'info': 'INFO',
                                'success': 'OK',
                                'warning': 'WARN',
                                'error': 'ERROR'
                            }[log.level] || 'INFO',
                            message: log.message
                        });
                    }
                }
                
                // Keep only last 100 logs
                if (this.logs.length > 100) {
                    this.logs = this.logs.slice(-100);
                }
                
                // Auto scroll
                if (this.autoScroll) {
                    this.$nextTick(() => {
                        const logList = this.$refs.logList;
                        if (logList) {
                            logList.scrollTop = logList.scrollHeight;
                        }
                    });
                }
            } catch (error) {
                console.error('Failed to fetch backend logs:', error);
            }
        },
        
        startLogPolling() {
            this.fetchBackendLogs();
            this.logPollingInterval = setInterval(() => {
                this.fetchBackendLogs();
            }, 5000);
        },
        
        // Subscriptions
        async loadSubscriptions() {
            try {
                this.addLog('info', '正在加载订阅列表...');
                const response = await axios.get('/api/subscriptions');
                this.subscriptions = response.data.items;
                this.addLog('success', `订阅加载完成，共 ${this.subscriptions.length} 个`);
            } catch (error) {
                this.addLog('error', '加载订阅失败: ' + (error.response?.data?.detail || error.message));
                this.showNotification('加载订阅失败', 'error');
                console.error('Load subscriptions error:', error);
            }
        },
        
        async addSubscription() {
            if (!this.newKeyword.trim()) return;
            
            try {
                this.addLog('info', `正在添加订阅: ${this.newKeyword.trim()}`);
                await axios.post('/api/subscriptions', {
                    keyword: this.newKeyword.trim()
                });
                
                this.addLog('success', `订阅 "${this.newKeyword.trim()}" 添加成功`);
                this.showNotification('订阅添加成功', 'success');
                this.showAddDialog = false;
                this.newKeyword = '';
                this.loadSubscriptions();
            } catch (error) {
                this.addLog('error', '添加订阅失败: ' + (error.response?.data?.detail || error.message));
                const message = error.response?.data?.detail || '添加订阅失败';
                this.showNotification(message, 'error');
                console.error('Add subscription error:', error);
            }
        },
        
        async toggleSubscription(subscription) {
            try {
                this.addLog('info', `正在${subscription.enabled ? '禁用' : '启用'}订阅: ${subscription.keyword}`);
                await axios.patch(
                    `/api/subscriptions/${subscription.id}/enabled?enabled=${!subscription.enabled}`
                );
                
                subscription.enabled = !subscription.enabled;
                this.addLog('success', `订阅 "${subscription.keyword}" 已${subscription.enabled ? '启用' : '禁用'}`);
                this.showNotification(
                    subscription.enabled ? '订阅已启用' : '订阅已禁用', 
                    'success'
                );
            } catch (error) {
                this.addLog('error', '更新订阅状态失败: ' + (error.response?.data?.detail || error.message));
                this.showNotification('更新订阅状态失败', 'error');
                console.error('Toggle subscription error:', error);
            }
        },
        
        async deleteSubscription(id) {
            const sub = this.subscriptions.find(s => s.id === id);
            if (!confirm('确定要删除这个订阅吗？')) return;
            
            try {
                this.addLog('warning', `正在删除订阅: ${sub?.keyword || id}`);
                await axios.delete(`/api/subscriptions/${id}`);
                this.addLog('success', `订阅 "${sub?.keyword || id}" 已删除`);
                this.showNotification('订阅已删除', 'success');
                this.loadSubscriptions();
            } catch (error) {
                this.addLog('error', '删除订阅失败: ' + (error.response?.data?.detail || error.message));
                this.showNotification('删除订阅失败', 'error');
                console.error('Delete subscription error:', error);
            }
        },
        
        // Reports
        async loadReports() {
            try {
                this.addLog('info', '正在加载日报列表...');
                const response = await axios.get('/api/reports');
                this.reports = response.data.items;
                this.addLog('success', `日报加载完成，共 ${this.reports.length} 篇`);
            } catch (error) {
                this.addLog('error', '加载日报失败: ' + (error.response?.data?.detail || error.message));
                this.showNotification('加载日报失败', 'error');
                console.error('Load reports error:', error);
            }
        },
        
        async collectArticles() {
            this.collecting = true;
            try {
                this.addLog('info', '🚀 开始搜集资讯...');
                
                const response = await axios.post('/api/reports/collect-articles', {});
                
                if (response.data.task_id) {
                    // New background task mode
                    const taskId = response.data.task_id;
                    this.addLog('info', `任务已提交 (ID: ${taskId.substring(0, 8)}...)`);
                    this.startTaskPolling(taskId, 'collect');
                    this.showNotification('资讯搜集已启动，正在后台运行...', 'success');
                } else {
                    // Legacy sync mode
                    this.addLog('success', '✅ 资讯搜集完成');
                    this.showNotification('资讯搜集完成', 'success');
                }
            } catch (error) {
                this.addLog('error', '搜集资讯失败: ' + (error.response?.data?.detail || error.message));
                this.showNotification('搜集资讯失败', 'error');
                console.error('Collect articles error:', error);
            } finally {
                this.collecting = false;
            }
        },
        
        async generateReport() {
            this.generating = true;
            
            try {
                this.addLog('info', '🚀 开始生成日报...');
                
                const response = await axios.post('/api/reports/generate', {});
                
                if (response.data.task_id) {
                    // New background task mode
                    const taskId = response.data.task_id;
                    this.addLog('info', `任务已提交 (ID: ${taskId.substring(0, 8)}...)`);
                    this.startTaskPolling(taskId, 'generate');
                    this.showNotification('日报生成已启动，正在后台运行...', 'success');
                } else {
                    // Legacy sync mode
                    this.addLog('success', '✅ 日报生成完成');
                    this.showNotification('日报生成完成', 'success');
                    this.loadReports();
                }
            } catch (error) {
                this.addLog('error', '❌ 生成日报失败: ' + (error.response?.data?.detail || error.message));
                this.showNotification('生成日报失败', 'error');
                console.error('Generate report error:', error);
            } finally {
                this.generating = false;
            }
        },
        
        async generateReportOnly() {
            this.generatingOnly = true;
            
            try {
                this.addLog('info', '📄 基于现有文章生成日报...');
                
                const response = await axios.post('/api/reports/generate-only', {});
                
                if (response.data.task_id) {
                    // New background task mode
                    const taskId = response.data.task_id;
                    this.addLog('info', `仅生成报告任务已提交 (ID: ${taskId.substring(0, 8)}...)`);
                    this.startTaskPolling(taskId, 'generate-only');
                    this.showNotification('仅生成日报已启动（基于现有文章）', 'success');
                } else {
                    // Legacy sync mode
                    this.addLog('success', '✅ 日报生成完成');
                    this.showNotification('日报生成完成', 'success');
                    this.loadReports();
                }
            } catch (error) {
                this.addLog('error', '❌ 生成日报失败: ' + (error.response?.data?.detail || error.message));
                this.showNotification('生成日报失败', 'error');
                console.error('Generate report only error:', error);
            } finally {
                this.generatingOnly = false;
            }
        },
        
        // Task polling methods
        startTaskPolling(taskId, taskType) {
            this.activeTasks.push({ id: taskId, type: taskType, progress: 0, status: 'running', logs: [] });
            this.showTaskDialog = true;
            this.currentTask = this.activeTasks.find(t => t.id === taskId);
            
            // Poll every 2 seconds
            const interval = setInterval(async () => {
                await this.pollTaskStatus(taskId);
            }, 2000);
            
            this.taskPollingIntervals[taskId] = interval;
            
            // Initial poll
            this.pollTaskStatus(taskId);
        },
        
        async pollTaskStatus(taskId) {
            try {
                const response = await axios.get(`/api/tasks/${taskId}`);
                const task = response.data;
                
                // Update active task
                const activeTask = this.activeTasks.find(t => t.id === taskId);
                if (activeTask) {
                    activeTask.progress = task.progress || 0;
                    activeTask.status = task.status;
                    activeTask.message = task.message;
                    activeTask.logs = task.logs || [];
                    
                    // Add new logs to main log panel
                    if (task.logs && task.logs.length > 0) {
                        const lastLogIndex = activeTask.lastLogIndex || 0;
                        for (let i = lastLogIndex; i < task.logs.length; i++) {
                            this.addLog('info', task.logs[i]);
                        }
                        activeTask.lastLogIndex = task.logs.length;
                    }
                }
                
                // Check if task is complete
                if (task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled') {
                    this.stopTaskPolling(taskId);
                    
                    if (task.status === 'completed') {
                        this.addLog('success', `✅ 任务完成: ${task.message || '成功'}`);
                        this.showNotification('任务完成', 'success');
                        
                        // Reload reports if it was a generate task
                        if (activeTask && (activeTask.type === 'generate' || activeTask.type === 'generate-only' || activeTask.type === 'full-pipeline')) {
                            setTimeout(() => this.loadReports(), 1000);
                        }
                    } else if (task.status === 'failed') {
                        this.addLog('error', `❌ 任务失败: ${task.error || '未知错误'}`);
                        this.showNotification('任务失败: ' + (task.error || '未知错误'), 'error');
                    } else {
                        this.addLog('warning', '任务已取消');
                        this.showNotification('任务已取消', 'warning');
                    }
                    
                    // Remove from active tasks after a delay
                    setTimeout(() => {
                        const index = this.activeTasks.findIndex(t => t.id === taskId);
                        if (index > -1) {
                            this.activeTasks.splice(index, 1);
                        }
                        if (this.activeTasks.length === 0) {
                            this.showTaskDialog = false;
                        }
                    }, 3000);
                }
            } catch (error) {
                console.error('Poll task status error:', error);
                // Don't stop polling on temporary errors
            }
        },
        
        stopTaskPolling(taskId) {
            if (this.taskPollingIntervals[taskId]) {
                clearInterval(this.taskPollingIntervals[taskId]);
                delete this.taskPollingIntervals[taskId];
            }
        },
        
        async cancelTask(taskId) {
            try {
                await axios.delete(`/api/tasks/${taskId}`);
                this.addLog('warning', '任务取消请求已发送');
            } catch (error) {
                this.addLog('error', '取消任务失败: ' + error.message);
            }
        },
        
        viewReport(report) {
            this.addLog('info', `查看日报: ${report.keyword} - ${report.date}`);
            this.viewingReport = report;  // report contains id, keyword, date
        },
        
        async downloadReport(reportId) {
            try {
                this.addLog('info', `下载日报 ID: ${reportId}`);
                window.open(`/api/reports/${reportId}/download`, '_blank');
                this.addLog('success', '日报下载已开始');
            } catch (error) {
                this.addLog('error', '下载日报失败: ' + error.message);
                this.showNotification('下载日报失败', 'error');
                console.error('Download report error:', error);
            }
        },
        
        downloadReportHtml(reportId) {
            this.addLog('info', `下载HTML: ID ${reportId}`);
            window.open(`/api/reports/${reportId}/download`, '_blank');
            this.addLog('success', 'HTML下载已开始');
        },
        
        async downloadReportAsPng(reportId) {
            try {
                this.addLog('info', `正在生成PNG截图...`);
                
                // Get the iframe element
                const iframe = this.$refs.reportIframe;
                if (!iframe) {
                    throw new Error('无法找到日报内容');
                }
                
                // Try to access iframe content
                const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                const iframeBody = iframeDoc.body;
                
                if (!iframeBody) {
                    throw new Error('无法访问日报内容');
                }
                
                // Use html2canvas if available
                if (typeof html2canvas === 'undefined') {
                    this.addLog('warning', 'PNG导出功能需要加载html2canvas库');
                    this.showNotification('PNG导出功能暂不可用，请下载HTML', 'warning');
                    return;
                }
                
                this.addLog('info', '正在渲染页面...');
                
                // Get body's actual content dimensions (excluding margins)
                const bodyStyle = window.getComputedStyle(iframeBody);
                const marginTop = parseInt(bodyStyle.marginTop) || 0;
                const marginLeft = parseInt(bodyStyle.marginLeft) || 0;
                
                // Capture the iframe content without margins
                const canvas = await html2canvas(iframeBody, {
                    allowTaint: true,
                    useCORS: true,
                    scale: 2,
                    backgroundColor: '#ffffff',
                    x: marginLeft,
                    y: marginTop,
                    width: iframeBody.scrollWidth - marginLeft - (parseInt(bodyStyle.marginRight) || 0),
                    height: iframeBody.scrollHeight - marginTop - (parseInt(bodyStyle.marginBottom) || 0),
                    scrollX: 0,
                    scrollY: 0
                });
                
                // Convert to blob and download
                canvas.toBlob((blob) => {
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `report_${reportId}_${new Date().getTime()}.png`;
                    a.click();
                    URL.revokeObjectURL(url);
                    
                    this.addLog('success', 'PNG下载成功');
                    this.showNotification('PNG已生成', 'success');
                });
                
            } catch (error) {
                this.addLog('error', 'PNG生成失败: ' + error.message);
                this.showNotification('PNG生成失败: ' + error.message, 'error');
                console.error('Download as PNG error:', error);
            }
        },
        
        // Schedule
        async loadSchedule() {
            try {
                const response = await axios.get('/api/schedule');
                this.schedule = {
                    time: response.data.time,
                    enabled: response.data.enabled
                };
            } catch (error) {
                this.showNotification('加载定时配置失败', 'error');
                console.error('Load schedule error:', error);
            }
        },
        
        async updateSchedule() {
            try {
                await axios.put('/api/schedule', this.schedule);
                this.showNotification('日报生成定时配置已更新', 'success');
            } catch (error) {
                this.showNotification('更新定时配置失败', 'error');
                console.error('Update schedule error:', error);
            }
        },
        
        // Crawl Schedule
        async loadCrawlSchedule() {
            try {
                const response = await axios.get('/api/schedule/crawl');
                this.crawlSchedule = {
                    enabled: response.data.enabled,
                    times: response.data.times || ['06:00', '12:00', '18:00', '22:00']
                };
            } catch (error) {
                console.error('Load crawl schedule error:', error);
                // Use default if API fails
                this.crawlSchedule = {
                    enabled: true,
                    times: ['06:00', '12:00', '18:00', '22:00']
                };
            }
        },
        
        async updateCrawlSchedule() {
            try {
                await axios.put('/api/schedule/crawl', this.crawlSchedule);
                this.showNotification('资讯采集定时配置已更新', 'success');
            } catch (error) {
                this.showNotification('更新采集定时配置失败', 'error');
                console.error('Update crawl schedule error:', error);
            }
        },
        
        addCrawlTime() {
            // Add a new time slot, default to next hour
            const lastTime = this.crawlSchedule.times[this.crawlSchedule.times.length - 1] || '12:00';
            const [hour, min] = lastTime.split(':').map(Number);
            const newHour = (hour + 4) % 24;  // Add 4 hours
            const newTime = `${String(newHour).padStart(2, '0')}:${String(min).padStart(2, '0')}`;
            this.crawlSchedule.times.push(newTime);
        },
        
        removeCrawlTime(index) {
            if (this.crawlSchedule.times.length > 1) {
                this.crawlSchedule.times.splice(index, 1);
                this.updateCrawlSchedule();
            }
        },
        
        // Utilities
        formatDate(dateString) {
            if (!dateString) return '';
            const date = new Date(dateString);
            return date.toLocaleDateString('zh-CN');
        },
        
        formatDateTime(dateString) {
            if (!dateString) return '';
            const date = new Date(dateString);
            return date.toLocaleString('zh-CN');
        },
        
        showNotification(message, type = 'info') {
            this.notification = { message, type };
            setTimeout(() => {
                this.notification = null;
            }, 3000);
        }
    }
}).mount('#app');
