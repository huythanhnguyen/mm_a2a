import axios from 'axios';

const API_URL = 'http://localhost:5000';

/**
 * Service để tương tác với API chatbot
 */
const chatService = {
  /**
   * Lấy thông tin profile người dùng
   * @param {string} userId - ID của người dùng
   * @param {string} sessionId - ID của phiên chat
   * @returns {Promise} Promise với kết quả từ API
   */
  getUserProfile: async (userId, sessionId) => {
    if (!userId || !sessionId) {
      console.warn('getUserProfile: Missing userId or sessionId');
      return null;
    }
    
    try {
      // Sử dụng GET để lấy thông tin profile
      const response = await axios.get(`${API_URL}/api/user-profile?user_id=${userId}&session_id=${sessionId}`);
      
      if (response.data && response.data.success && 
          response.data.data && response.data.data.user_profile) {
        return response.data.data.user_profile;
      }
      
      return {};
    } catch (error) {
      console.error('Get user profile error:', error);
      // Trả về đối tượng trống thay vì null để tránh lỗi
      return {};
    }
  }
};

export default chatService; 