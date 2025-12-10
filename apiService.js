import axios from "axios";
import { API_BASE_URL, apiClient } from "../../../config";
import {
  handleApiError,
  handleApiErrorWithValidation,
} from "../../../utils/helpers";

// Function to refresh access token
const refreshAccessToken = async () => {
  try {
    const refreshToken = localStorage.getItem("refreshToken");
    if (!refreshToken) {
      throw new Error("No refresh token available");
    }

    const response = await axios.post(`${API_BASE_URL}/api/token/refresh/`, {
      refresh: refreshToken,
    });

    const newAccessToken = response.data.access;
    localStorage.setItem("accessToken", newAccessToken);
    return newAccessToken;
  } catch (error) {
    console.error("Error refreshing token:", error);
    localStorage.removeItem("accessToken");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("tenantId");
    localStorage.removeItem("tenantSchema");
    localStorage.removeItem("user");
    window.location.href = "/";
    throw new Error("Session expired. Please log in again.");
  }
};

// Request interceptor to include access token
apiClient.interceptors.request.use(
  async (config) => {
    const token = localStorage.getItem("accessToken");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor to handle token expiration
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const newToken = await refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export const createRequisition = async (requisitionData) => {
  try {
    const response = await apiClient.post(
      "/api/talent-engine/requisitions/",
      requisitionData
    );
    return response.data;
  } catch (error) {
    console.error("Create requisition error:", error.response?.data);
    handleApiErrorWithValidation(error);
  }
};

export const fetchRequisition = async (id) => {
  try {
    const response = await apiClient.get(
      `/api/talent-engine/requisitions/${id}/`
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const bulkDeleteRequisitions = async (ids) => {
  try {
    if (!ids.every((id) => typeof id === "string" )) {
      throw new Error(
        "Invalid IDs provided. All IDs must be in the format PRO-XXXX."
      );
    }
    const config = {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("accessToken")}`,
      },
    };
    const response = await apiClient.post(
      "/api/talent-engine/requisitions/bulk/bulk-delete/",
      { ids },
      config
    );
    return response.data;
  } catch (error) {
    console.error("Bulk soft delete error:", {
      message: error.message,
      response: error.response?.data,
      status: error.response?.status,
    });
    handleApiError(error);
  }
};

export const fetchAllRequisitions = async (params = {}) => {
  try {
    const response = await apiClient.get("/api/talent-engine/requisitions/", {
      params,
    });
    return {
      results: response.data.results,
      count: response.data.count,
      next: response.data.next,
      previous: response.data.previous,
    };
  } catch (error) {
    console.log(error.status);
    handleApiError(error);
  }
};

export const fetchStaffRequisitions = async (id) => {
  try {
    const response = await apiClient.get(
      `/api/talent-engine/requisitions-per-user`
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const updateRequisition = async (id, requisitionData) => {
  try {
    const response = await apiClient.patch(
      `/api/talent-engine/requisitions/${id}/`,
      requisitionData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

export const deleteRequisition = async (id) => {
  try {
    await apiClient.delete(`/api/talent-engine/requisitions/${id}/`);
    return true;
  } catch (error) {
    handleApiError(error);
  }
};

export const fetchSoftDeletedRequisitions = async () => {
  try {
    const response = await apiClient.get(
      "/api/talent-engine/requisitions/deleted/soft_deleted/"
    );
    return response.data.data || response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const recoverRequisitions = async (ids) => {
  try {
    const response = await apiClient.post(
      "/api/talent-engine/requisitions/recover/requisition/",
      { ids }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const permanentDeleteRequisitions = async (ids) => {
  try {
    const response = await apiClient.post(
      "/api/talent-engine/requisitions/permanent-delete/requisition/",
      { ids }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const updateRequisitionStatus = async (id, status) => {
  try {
    const response = await apiClient.patch(
      `/api/talent-engine/requisitions/${id}/`,
      { status }
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

export const togglePublishRequisition = async (id, publishStatus) => {
  try {
    const response = await apiClient.patch(
      `/api/talent-engine/requisitions/${id}/`,
      { publish_status: publishStatus }
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

// API function to fetch all job applications
export const fetchAllJobApplications = async () => {
  try {
    const response = await apiClient.get(
      "/api/applications-engine/applications/"
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const fetchJobApplicationById = async (applicationId) => {
  try {
    const response = await apiClient.get(
      `/api/applications-engine/applications/${applicationId}/`
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// API function to fetch job applications by requisition
export const fetchJobApplicationsByRequisition = async (jobId) => {
  try {
    const response = await apiClient.get(
      `/api/applications-engine/applications/job-requisitions/${jobId}/applications/`
    );
    return {
      results: response.data.results,
      count: response.data.count,
      next: response.data.next,
      previous: response.data.previous,
    };
  } catch (error) {
    handleApiError(error);
  }
};

// API function to fetch soft-deleted job applications
export const fetchSoftDeletedJobApplications = async () => {
  try {
    const response = await apiClient.get(
      "/api/applications-engine/applications/deleted/soft_deleted/"
    );
    return response.data.data || response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// API function to recover soft-deleted job applications
export const recoverJobApplications = async (ids) => {
  try {
    const response = await apiClient.post(
      "/api/applications-engine/applications/recover/application/",
      { ids }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// API function to permanently delete job applications
export const permanentDeleteJobApplications = async (ids) => {
  try {
    const response = await apiClient.post(
      "/api/applications-engine/applications/permanent-delete/application/",
      { ids }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// API function to update job application status
export const updateJobApplicationStatus = async (id, data) => {
  try {
    const response = await apiClient.put(
      `/api/applications-engine/applications/${id}/`,
      data,
      {
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

// API function to bulk delete job applications
export const bulkDeleteJobApplications = async (ids) => {
  try {
    const response = await apiClient.post(
      "/api/applications-engine/applications/bulk-delete/applications/",
      { ids }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// API function to screen resumes for a job requisition
export const screenResumes = async (jobRequisitionId, data) => {
  try {
    const response = await apiClient.post(
      `/api/applications-engine/requisitions/${jobRequisitionId}/screen-resumes/`,
      data
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

export const resendRejectionEmails = async (
  jobRequisitionId,
  applicationIds
) => {
  try {
    const response = await apiClient.post(
      `/api/applications-engine/requisitions/${jobRequisitionId}/resend-rejection-emails/`,
      { application_ids: applicationIds }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// API function to fetch published requisitions with shortlisted applications
export const fetchPublishedRequisitionsWithShortlisted = async () => {
  try {
    const response = await apiClient.get(
      "/api/applications-engine/published-requisitions-with-shortlisted/"
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const createSchedule = async (scheduleData) => {
  try {
    const response = await apiClient.post(
      "/api/applications-engine/schedules/",
      scheduleData
    );
    return response.data;
  } catch (error) {
    const errorDetails = error.response?.data || {};

    // Keep custom email error handling
    if (
      errorDetails.detail &&
      errorDetails.detail.includes("Failed to send email")
    ) {
      throw {
        message: errorDetails.detail,
        error: errorDetails.error || "Unable to send confirmation email.",
        suggestion:
          errorDetails.suggestion ||
          "Please check email settings in the tenant configuration.",
      };
    }

    // For other errors, use the validation-enhanced utility
    handleApiErrorWithValidation(error);
  }
};

export const fetchSchedules = async (params = {}) => {
  try {
    const response = await apiClient.get(
      "/api/applications-engine/schedules/",
      { params }
    );
    return {
      results: response.data.results,
      count: response.data.count,
      next: response.data.next,
      previous: response.data.previous,
    };
  } catch (error) {
    handleApiError(error);
  }
};

export const updateSchedule = async (id, scheduleData) => {
  try {
    const response = await apiClient.patch(
      `/api/applications-engine/schedules/${id}/`,
      scheduleData
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

export const completeSchedule = async (id) => {
  try {
    const response = await apiClient.patch(
      `/api/applications-engine/schedules/${id}/`,
      {
        status: "completed",
      }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const cancelSchedule = async (id, cancellationReason) => {
  try {
    const response = await apiClient.patch(
      `/api/applications-engine/schedules/${id}/`,
      {
        status: "cancelled",
        cancellation_reason: cancellationReason,
      }
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

export const resetSchedule = async (id) => {
  try {
    const response = await apiClient.patch(
      `/api/applications-engine/schedules/${id}/`,
      {
        status: "scheduled",
      }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const deleteSchedule = async (id) => {
  try {
    await apiClient.delete(`/api/applications-engine/schedules/${id}/`);
    return true;
  } catch (error) {
    handleApiError(error);
  }
};

export const bulkDeleteSchedules = async (ids) => {
  try {
    console.log("Sending bulk delete request:", { ids });
    const response = await apiClient.post(
      "/api/applications-engine/schedules/bulk-delete/",
      { ids }
    );
    console.log("Bulk delete response:", response.data);
    return response.data;
  } catch (error) {
    console.error("Bulk delete error:", error.response?.data);
    handleApiError(error);
  }
};

export const fetchSoftDeletedSchedules = async () => {
  try {
    const response = await apiClient.get(
      "/api/applications-engine/schedules/deleted/soft_deleted/"
    );
    return response.data.data || response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const recoverSchedules = async (ids) => {
  try {
    const response = await apiClient.post(
      "/api/applications-engine/schedules/recover/schedule/",
      { ids }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const permanentDeleteSchedules = async (ids) => {
  try {
    const response = await apiClient.post(
      "/api/applications-engine/schedules/permanent-delete/schedule/",
      { ids }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const fetchTimezoneChoices = async () => {
  try {
    const response = await apiClient.get(
      "/api/applications-engine/schedules/api/timezone-choices/"
    );
    const data = response.data.data || response.data;

    if (
      !Array.isArray(data) ||
      !data.every(
        (tz) => typeof tz === "object" && "value" in tz && "label" in tz
      )
    ) {
      throw new Error("Invalid timezone choices format");
    }

    return data;
  } catch (error) {
    handleApiError(error);
  }
};

// API function to fetch tenant email configuration
// export const fetchTenantConfig = async () => {
//   try {
//     const token = localStorage.getItem("accessToken");
//     if (!token) {
//       throw new Error("No access token available");
//     }
//     const base64Url = token.split(".")[1];
//     const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
//     const payload = JSON.parse(atob(base64));
//     const tenantId = payload.tenant_unique_id;
//     const response = await apiClient.get(`api/tenant/tenants/${tenantId}/`);
//     return response.data;
//   } catch (error) {
//     handleApiError(error);
//   }
// };

// // API function to update tenant email configuration
// export const updateTenantConfig = async (id, configData) => {
//   try {
//     const token = localStorage.getItem("accessToken");
//     if (!token) {
//       throw new Error("No access token available");
//     }
//     const base64Url = token.split(".")[1];
//     const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
//     const payload = JSON.parse(atob(base64));
//     const tenantId = payload.tenant_id;
//     const response = await apiClient.patch(
//       `api/tenant/tenants/${tenantId}/`,
//       configData
//     );
//     return response.data;
//   } catch (error) {
//     handleApiErrorWithValidation(error);
//   }
// };

// Helper to get the current tenant ID
export const getCurrentTenantUniqueId = () => {
  const tenantUniqueId = localStorage.getItem("tenantUniqueId");
  // Example: return localStorage.getItem('tenantUniqueId') || '09145372-eb5d-40ff-9d93-ca49425a16e6';
  return tenantUniqueId || "default-tenant"; // Fallback for development
};

// Fetch tenant configuration
export const fetchTenantConfig = async () => {
  try {
    const tenantUniqueId = getCurrentTenantUniqueId();
    const response = await apiClient.get(
      `/api/tenants/tenants/${tenantUniqueId}/`
    );
    const data = response.data;

    // Add dates if not present
    data.created_date = data.created_at
      ? data.created_at.split("T")[0]
      : new Date().toISOString().split("T")[0];
    data.last_modified =
      data.updated_at ||
      data.created_at ||
      `${
        new Date().toISOString().split("T")[0]
      } ${new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })}`;

    // Use tenantId as id if not present
    data.id = data.id || tenantUniqueId;
    return data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// Update tenant configuration
export const updateTenantConfig = async (emailProviderId, configData) => {
  try {
    const payload = {
      ...configData,
      isDefault: true, // Always set to true as per requirement
    };

    const response = await apiClient.put(
      `/tenants/global/email-providers/${emailProviderId}`,
      payload
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
    throw error;
  }
};

// Create tenant configuration
export const createTenantConfig = async (configData) => {
  try {
    const tenantUniqueId = getCurrentTenantUniqueId();

    const payload = {
      ...configData,
      isDefault: true, // Always set to true
    };

    const response = await apiClient.post(
      `/api/notifications/tenants/${tenantUniqueId}/email-providers/`,
      payload
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
    throw error;
  }
};

export const updateTenantInfo = async (tenantData) => {
  try {
    const token = localStorage.getItem("accessToken");
    if (!token) {
      throw new Error("No access token available");
    }
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(base64));
    const tenantId = payload.tenant_unique_id;
    const response = await apiClient.patch(
      `/api/tenant/tenants/${tenantId}/`,
      tenantData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      }
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

export const createComplianceItem = async (jobRequisitionId, itemData) => {
  try {
    const response = await apiClient.post(
      `/api/talent-engine/requisitions/${jobRequisitionId}/compliance-items/`,
      itemData
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

export const updateApplicantComplianceStatus = async (
  jobApplicationId,
  itemId,
  data
) => {
  try {
    const response = await apiClient.put(
      `/api/applications-engine/applications/compliance/${jobApplicationId}/compliance-items/${itemId}/`,
      data
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

export const deleteComplianceItem = async (jobRequisitionId, itemId) => {
  try {
    const response = await apiClient.delete(
      `/api/talent-engine/requisitions/${jobRequisitionId}/compliance-items/${itemId}/`
    );
    return response.data;
  } catch (error) {
    console.error("Error deleting compliance item:", error);
    handleApiError(error);
  }
};

export const updateComplianceItem = async (jobRequisitionId, itemId, data) => {
  try {
    const response = await apiClient.put(
      `/api/talent-engine/requisitions/${jobRequisitionId}/compliance-items/${itemId}/`,
      data
    );
    return response.data;
  } catch (error) {
    console.error("Error updating compliance item:", error);
    handleApiErrorWithValidation(error);
  }
};

export const fetchTenantEmailConfig = async () => {
  try {
    const response = await apiClient.get(
      "/api/tenant/config/?t=" + new Date().getTime()
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const updateTenantEmailConfig = async (configData) => {
  try {
    const response = await apiClient.patch("/api/tenant/config/", configData);
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

export const fetchBranches = async () => {
  try {
    const response = await apiClient.get("/api/tenant/tenants/branches/");
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const createBranch = async (branchData) => {
  try {
    const response = await apiClient.post("/api/tenant/branches/", branchData);
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

// Video sessions APIs
export const createVideoSession = async (sessionData) => {
  try {
    const response = await apiClient.post(
      `/api/talent-engine/video-sessions/`,
      sessionData
    );
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
  }
};

export const getVideoSession = async (sessionId) => {
  try {
    const response = await axios.get(
      `/api/talent-engine/video-sessions/${sessionId}`
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const joinVideoSession = async (sessionId, userId) => {
  try {
    const response = await axios.post(
      `/api/talent-engine/video-sessions/join`,
      {
        session_id: sessionId,
        user_id: userId,
      }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const leaveVideoSession = async (sessionId, userId) => {
  try {
    const response = await axios.post(
      `/api/talent-engine/video-sessions/leave`,
      {
        session_id: sessionId,
        user_id: userId,
      }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const startRecording = async (sessionId) => {
  try {
    const response = await axios.post(
      `/api/talent-engine/video-sessions/start_recording`,
      {
        session_id: sessionId,
      }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const stopRecording = async (sessionId) => {
  try {
    const response = await axios.post(
      `/api/talent-engine/video-sessions/start_recording`,
      {
        session_id: sessionId,
        action: "stop",
      }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const toggleCamera = async (sessionId, userId, status) => {
  try {
    const response = await axios.post(
      `/api/talent-engine/video-sessions/toggle_camera`,
      {
        session_id: sessionId,
        user_id: userId,
        status: status,
      }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

export const toggleMute = async (sessionId, userId, status) => {
  try {
    const response = await axios.post(
      `/api/talent-engine/video-sessions/toggle_mute`,
      {
        session_id: sessionId,
        user_id: userId,
        status: status,
      }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// Video feature API
export const getJitsiToken = async (room) => {
  try {
    const response = await apiClient.post("/api/jitsi/token/", {
      room,
    });
    return response.data?.token;
  } catch (err) {
    console.error("Failed to fetch Jitsi token:", err);
    handleApiError(err);
  }
};

// Add this to your ApiService.js
export const checkScreeningTaskStatus = async (taskId) => {
  try {
    const response = await apiClient.get(
      `/api/applications-engine/requisitions/screening/task-status/${taskId}/`
    );
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || "Failed to check screening task status."
    );
  }
};


// ──────────────────────────────────────────────────────────────────────────────
//  Add this near the bottom of the file (anywhere after the other exports)
// ──────────────────────────────────────────────────────────────────────────────
export const fetchAllUsers = async (params = {}) => {
  try {
    const response = await apiClient.get("/api/user/users/", { params });
    // The endpoint returns { count, next, previous, results }
    return {
      results: response.data.results,
      count: response.data.count,
      next: response.data.next,
      previous: response.data.previous,
    };
  } catch (error) {
    // Re-use the same error helper you already have
    handleApiError(error);
    // Throw so the component can catch it
    throw error;
  }
};

// ──────────────────────────────────────────────────────────────────────────────
//  Messaging API Functions
// ──────────────────────────────────────────────────────────────────────────────

// Get all users for messaging (paginated)
export const fetchMessagingUsers = async (params = {}) => {
  try {
    const response = await apiClient.get("/api/messaging/users", { params });
    return {
      results: response.data.results,
      count: response.data.count,
      next: response.data.next,
      previous: response.data.previous,
    };
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// Get user's chats
export const fetchUserChats = async () => {
  try {
    // Use the conversations endpoint (per MESSAGING.MD) and normalize
    const response = await apiClient.get("/api/notifications/chat/conversations/");
    const data = response.data;

    // Normalize list: support different backend shapes ({ results: [...] } or plain array)
    const list = Array.isArray(data) ? data : (data.results || data.data || []);

    // Map to the shape the UI expects (id, name, participants, unreadCount, updatedAt)
    const mapped = (list || []).map((conv) => ({
      id: conv.id,
      name:
        conv.title ||
        (conv.participants && conv.participants[0] && (conv.participants[0].displayName || conv.participants[0].username)) ||
        conv.name ||
        "Conversation",
      participants: conv.participants || [],
      unreadCount: conv.unread_count || conv.unreadCount || conv.unread || 0,
      updatedAt: conv.last_message_at || conv.updated_at || conv.updatedAt || null,
    }));

    return mapped;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// Create or get direct chat
export const createDirectChat = async (participantId) => {
  try {
    // Use the conversations endpoint to create a direct conversation
    // The documentation specifies creating conversations at:
    // POST /api/notifications/chat/conversations/
    const payload = {
      title: null,
      conversation_type: "direct",
      participants: [participantId],
    };
    const response = await apiClient.post(
      "/api/notifications/chat/conversations/",
      payload
    );
    // Return the created conversation (shape depends on backend; follow createChatConversation)
    return response.data;
  } catch (error) {
    // Use validation-aware handler when creating conversations
    handleApiErrorWithValidation(error);
    throw error;
  }
};

// Get chat messages
export const fetchChatMessages = async (chatId, params = {}) => {
  try {
    const response = await apiClient.get(`/api/messaging/messages/${chatId}`, { params });
    return response.data.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// Send message to user
export const sendMessageToUser = async (recipientId, content) => {
  try {
    const response = await apiClient.post("/api/messaging/messages/send", {
      recipientId,
      content,
    });
    return response.data.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// Send message by email
export const sendMessageByEmail = async (recipientEmail, content) => {
  try {
    const response = await apiClient.post("/api/messaging/messages/send-by-email", {
      recipientEmail,
      content,
    });
    return response.data.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// Send message to existing chat
export const sendMessageToChat = async (chatId, content) => {
  try {
    const response = await apiClient.post("/api/messaging/messages/send", {
      recipientId: chatId,
      content,
    });
    return response.data.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// Mark messages as read
export const markMessagesAsRead = async (chatId, messageId) => {
  try {
    const response = await apiClient.patch(`/api/messaging/chats/${chatId}/messages/${messageId}/read`);
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// ──────────────────────────────────────────────────────────────────────────────
//  Chat System API Functions (according to MESSAGING.MD documentation)
// ──────────────────────────────────────────────────────────────────────────────

// Conversations
export const fetchChatConversations = async (params = {}) => {
  try {
    const response = await apiClient.get("/api/notifications/chat/conversations/", { params });
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

export const createChatConversation = async (conversationData) => {
  try {
    const response = await apiClient.post("/api/notifications/chat/conversations/", conversationData);
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
    throw error;
  }
};

export const getChatConversation = async (conversationId) => {
  try {
    const response = await apiClient.get(`/api/notifications/chat/conversations/${conversationId}/`);
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

export const updateChatConversation = async (conversationId, conversationData) => {
  try {
    const response = await apiClient.put(`/api/notifications/chat/conversations/${conversationId}/`, conversationData);
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
    throw error;
  }
};

export const deleteChatConversation = async (conversationId) => {
  try {
    const response = await apiClient.delete(`/api/notifications/chat/conversations/${conversationId}/`);
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// Participants
export const fetchConversationParticipants = async (conversationId, params = {}) => {
  try {
    const response = await apiClient.get(`/api/notifications/chat/conversations/${conversationId}/participants/`, { params });
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

export const addConversationParticipant = async (conversationId, participantData) => {
  try {
    const response = await apiClient.post(`/api/notifications/chat/conversations/${conversationId}/participants/`, participantData);
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
    throw error;
  }
};

// Messages
export const fetchConversationMessages = async (conversationId, params = {}) => {
  try {
    const response = await apiClient.get(`/api/notifications/chat/conversations/${conversationId}/messages/`, { params });
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

export const sendConversationMessage = async (conversationId, messageData) => {
  try {
    const response = await apiClient.post(`/api/notifications/chat/conversations/${conversationId}/messages/`, messageData);
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
    throw error;
  }
};

export const getConversationMessage = async (conversationId, messageId) => {
  try {
    const response = await apiClient.get(`/api/notifications/chat/conversations/${conversationId}/messages/${messageId}/`);
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

export const updateConversationMessage = async (conversationId, messageId, messageData) => {
  try {
    const response = await apiClient.put(`/api/notifications/chat/conversations/${conversationId}/messages/${messageId}/`, messageData);
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
    throw error;
  }
};

export const deleteConversationMessage = async (conversationId, messageId) => {
  try {
    const response = await apiClient.delete(`/api/notifications/chat/conversations/${conversationId}/messages/${messageId}/`);
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// Reactions
export const fetchMessageReactions = async (messageId, params = {}) => {
  try {
    const response = await apiClient.get(`/api/notifications/chat/messages/${messageId}/reactions/`, { params });
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

export const addMessageReaction = async (messageId, reactionData) => {
  try {
    const response = await apiClient.post(`/api/notifications/chat/messages/${messageId}/reactions/`, reactionData);
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
    throw error;
  }
};

// Presence
export const fetchUserPresence = async (params = {}) => {
  try {
    const response = await apiClient.get("/api/notifications/chat/presence/", { params });
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

export const getMyPresence = async () => {
  try {
    const response = await apiClient.get("/api/notifications/chat/presence/me/");
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

export const updateMyPresence = async (presenceData) => {
  try {
    const response = await apiClient.put("/api/notifications/chat/presence/me/", presenceData);
    return response.data;
  } catch (error) {
    handleApiErrorWithValidation(error);
    throw error;
  }
};

// File Upload
export const uploadChatFile = async (file) => {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post("/api/notifications/chat/upload/", formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// ──────────────────────────────────────────────────────────────────────────────
//  Notification API Functions
// ──────────────────────────────────────────────────────────────────────────────

// Fetch in-app messages
export const fetchInAppMessages = async (params = {}) => {
  try {
    const response = await apiClient.get("/api/notifications/inapp-messages/", { params });
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};

// Mark message as read
export const markMessageAsRead = async (messageId) => {
  try {
    const response = await apiClient.post(`/api/notifications/inapp-messages/${messageId}/mark-read/`);
    return response.data;
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};