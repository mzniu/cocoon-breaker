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
            showAddDialog: false,
            newKeyword: '',
            generating: false,
            collecting: false,
            viewingReport: null,
            notification: null,
            // Log panel
            logs: [],
            logCollapsed: false,
            autoScroll: true,
            logPollingInterval: null,
            lastLogTimestamp: null
        };
    },
    
    mounted() {
        this.addLog('info', '🚀 应用已启动');
        this.loadSubscriptions();
        this.loadReports();
        this.loadSchedule();
        
        // Start log polling (every 5 seconds)
        this.startLogPolling();
    },
    
    beforeUnmount() {
        // Clean up polling interval
        if (this.logPollingInterval) {
            clearInterval(this.logPollingInterval);
        }
    },
    
    methods: {
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
                this.addLog('info', '步骤 1/2: 获取启用的订阅');
                
                await axios.post('/api/reports/collect-articles', {});
                
                this.addLog('info', '步骤 2/2: 爬取文章数据');
                this.addLog('success', '✅ 资讯搜集已启动，请稍后查看文章列表');
                this.showNotification('资讯搜集已启动', 'success');
            } catch (error) {
                this.addLog('error', '搜集资讯失败: ' + error.message);
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
                this.addLog('info', '步骤 1/4: 获取启用的订阅');
                await axios.post('/api/reports/generate', {});
                this.addLog('info', '步骤 2/4: 爬取文章数据');
                this.addLog('info', '步骤 3/4: AI 筛选与摘要');
                this.addLog('info', '步骤 4/4: 生成 HTML 日报');
                this.addLog('success', '✅ 日报生成已启动，请稍后查看结果');
                this.showNotification('日报生成已启动，请稍后刷新查看', 'success');
                
                // Reload reports after a delay
                setTimeout(() => {
                    this.loadReports();
                }, 3000);
            } catch (error) {
                this.addLog('error', '❌ 生成日报失败: ' + (error.response?.data?.detail || error.message));
                this.showNotification('生成日报失败', 'error');
                console.error('Generate report error:', error);
            } finally {
                this.generating = false;
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
                this.showNotification('定时配置已更新', 'success');
            } catch (error) {
                this.showNotification('更新定时配置失败', 'error');
                console.error('Update schedule error:', error);
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
